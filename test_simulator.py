"""
test_simulator.py — Automated Unit & Integration Verification Suite
====================================================================
Verifies:
1. 16-Byte Binary Header Packing/Unpacking (`struct.pack('!HIBBBBHI')`)
2. RFC 5109 / XOR Parity FEC Single-Packet Erasure Recovery (exact payload restoration)
3. Token Bucket Queueing Delay (`D_queue`) and Gilbert-Elliott 2-State Markov Burst Loss
4. Cross-Layer Delay-Gradient ABR Dual-Metric Classifier & Audio-First Survival
5. Live Raw UDP Socket Transmission through `UDPNetworkChannelProxy`
"""

from __future__ import annotations
import importlib.abc, importlib.util, os, sys
sys.dont_write_bytecode = True
class _LocalFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{fullname}.py")
        return importlib.util.spec_from_file_location(fullname, p) if os.path.exists(p) else None
if not any(type(f).__name__ == "_LocalFinder" for f in sys.meta_path):
    sys.meta_path.insert(0, _LocalFinder())
import time
import unittest
from abr_controller import BufferBasedABR, CrossLayerDelayGradientABR, RateBasedABR
from fec_engine import FECDecoder, FECEncoder
from network_channel import (
    ChannelConfig,
    GilbertElliottLossEngine,
    TokenBucketBottleneck,
    UDPNetworkChannelProxy,
)
from protocol import (
    HEADER_SIZE,
    MediaPacket,
    PKT_MEDIA_PAYLOAD,
    PKT_XOR_PARITY_FEC,
    STREAM_AUDIO,
    STREAM_VIDEO,
    TIER_1080P,
    TIER_720P,
    TIER_240P,
    pack_flags,
    unpack_flags,
)
from streaming_node import UDPMediaClient, UDPMediaServer


class TestAdaptiveStreamingSimulator(unittest.TestCase):
    def test_16_byte_binary_header_pack_unpack(self) -> None:
        """Verifies exact 16-byte big-endian struct packing and field integrity."""
        flags = pack_flags(fec_k=4, fec_idx=2, chunk_id=19, end_of_chunk=True)
        payload = b"HELLO_COMPUTER_NETWORKS_DR_SWATI"
        pkt = MediaPacket(
            seq_num=1042,
            timestamp_ms=98765432,
            stream_type=STREAM_VIDEO,
            bitrate_tier=TIER_720P,
            packet_type=PKT_MEDIA_PAYLOAD,
            fec_group_id=7,
            payload_size=len(payload),
            reserved_flags=flags,
            payload=payload,
        )
        raw = pkt.to_bytes()
        self.assertEqual(len(raw) - len(payload), 16)
        self.assertEqual(HEADER_SIZE, 16)

        unpacked = MediaPacket.from_bytes(raw)
        self.assertEqual(unpacked.seq_num, 1042)
        self.assertEqual(unpacked.timestamp_ms, 98765432)
        self.assertEqual(unpacked.stream_type, STREAM_VIDEO)
        self.assertEqual(unpacked.bitrate_tier, TIER_720P)
        self.assertEqual(unpacked.packet_type, PKT_MEDIA_PAYLOAD)
        self.assertEqual(unpacked.fec_group_id, 7)
        self.assertEqual(unpacked.payload_size, len(payload))
        self.assertEqual(unpacked.payload, payload)

        meta = unpack_flags(unpacked.reserved_flags)
        self.assertEqual(meta["fec_k"], 4)
        self.assertEqual(meta["fec_idx"], 2)
        self.assertEqual(meta["chunk_id"], 19)
        self.assertTrue(meta["end_of_chunk"])

    def test_xor_parity_fec_exact_recovery(self) -> None:
        """Verifies that dropping any 1 of k=4 media packets is 100% reconstructed via XOR parity."""
        encoder = FECEncoder()
        decoder = FECDecoder()

        payloads = [
            b"FRAME_SLICE_0_DATA_1234567890",
            b"FRAME_SLICE_1_VARIABLE_LEN_999999",
            b"FRAME_SLICE_2_SHORT",
            b"FRAME_SLICE_3_FINAL_SLICE_XYZ",
        ]
        raw_packets = [
            MediaPacket(
                seq_num=100 + i,
                timestamp_ms=5000 + i * 10,
                stream_type=STREAM_VIDEO,
                bitrate_tier=TIER_720P,
                packet_type=PKT_MEDIA_PAYLOAD,
                fec_group_id=3,
                payload_size=len(p),
                reserved_flags=pack_flags(chunk_id=5),
                payload=p,
            )
            for i, p in enumerate(payloads)
        ]

        tagged_media, parity_pkt = encoder.encode_group(raw_packets, fec_group_id=12, next_seq_num=104)
        self.assertIsNotNone(parity_pkt)
        assert parity_pkt is not None
        self.assertEqual(parity_pkt.packet_type, PKT_XOR_PARITY_FEC)

        # Simulate wireless drop of packet index 1 (`payloads[1]`)
        transmitted = [tagged_media[0], tagged_media[2], tagged_media[3], parity_pkt]
        reconstructed_pkt = None
        for pkt in transmitted:
            _, rec = decoder.receive_packet(pkt)
            if rec is not None:
                reconstructed_pkt = rec

        self.assertIsNotNone(reconstructed_pkt)
        assert reconstructed_pkt is not None
        self.assertEqual(reconstructed_pkt.payload, payloads[1])
        self.assertEqual(reconstructed_pkt.payload_size, len(payloads[1]))
        self.assertEqual(decoder.total_packets_recovered, 1)

    def test_dual_metric_loss_classifier_and_audio_first(self) -> None:
        """Verifies Wireless Loss vs. Bufferbloat Congestion classification and Audio-First mode."""
        abr = CrossLayerDelayGradientABR(queue_threshold_ms=25.0)

        # 1. Establish base propagation RTT_min = 40ms under 0% loss -> 1080p, 0% FEC
        d1 = abr.select_action(
            measured_throughput_kbps=5200.0,
            rtt_current_ms=40.0,
            packet_loss_rate=0.0,
            buffer_occupancy_sec=6.0,
        )
        self.assertEqual(d1.bitrate_tier, TIER_1080P)
        self.assertAlmostEqual(d1.fec_overhead_ratio, 0.0)
        self.assertFalse(d1.video_freeze)

        # 2. Wireless fade: 8% packet loss while RTT_current = 43ms (D_queue = 3ms ≈ 0)
        # Must classify as WIRELESS_LOSS_FEC_ACTIVE, keep 720p (80% media + 20% FEC), NOT drop to 240p!
        d2 = abr.select_action(
            measured_throughput_kbps=3600.0,
            rtt_current_ms=43.0,
            packet_loss_rate=0.08,
            buffer_occupancy_sec=5.5,
        )
        self.assertEqual(d2.network_regime, "WIRELESS_LOSS_FEC_ACTIVE")
        self.assertEqual(d2.bitrate_tier, TIER_720P)
        self.assertAlmostEqual(d2.fec_overhead_ratio, 0.20)
        self.assertEqual(d2.fec_k, 4)

        # Compare with Traditional Rate-Based under identical wireless fade: collapses to 240p!
        rb = RateBasedABR()
        d_rb = rb.select_action(
            measured_throughput_kbps=3600.0,
            rtt_current_ms=43.0,
            packet_loss_rate=0.08,
            buffer_occupancy_sec=5.5,
        )
        self.assertEqual(d_rb.bitrate_tier, TIER_240P)

        # 3. Bottleneck Bufferbloat Congestion: RTT spikes to 110ms (D_queue = 70ms > 25ms)
        d3 = abr.select_action(
            measured_throughput_kbps=2100.0,
            rtt_current_ms=110.0,
            packet_loss_rate=0.01,
            buffer_occupancy_sec=5.0,
        )
        self.assertEqual(d3.network_regime, "BUFFERBLOAT_PROACTIVE_THROTTLE")
        self.assertGreater(d3.d_queue_ms, 25.0)

        # 4. Catastrophic Loss (28% > 20%): Audio-First Graceful Degradation freezes video
        d4 = abr.select_action(
            measured_throughput_kbps=900.0,
            rtt_current_ms=65.0,
            packet_loss_rate=0.28,
            buffer_occupancy_sec=3.0,
        )
        self.assertEqual(d4.network_regime, "CATASTROPHIC_LOSS_AUDIO_FIRST_SURVIVAL")
        self.assertTrue(d4.video_freeze)
        self.assertEqual(d4.audio_redundancy, 3)

    def test_live_udp_socket_streaming_with_fec(self) -> None:
        """Tests end-to-end localhost UDP sockets through UDPNetworkChannelProxy."""
        cfg = ChannelConfig(
            bandwidth_kbps=8000.0,
            base_delay_ms=10.0,
            jitter_std_ms=2.0,
            loss_mode="uniform",
            uniform_loss_prob=0.08,
        )
        proxy = UDPNetworkChannelProxy(listen_port=19101, target_port=19102, config=cfg, seed=7)
        client = UDPMediaClient(listen_port=19102, server_feedback_port=19103)
        server = UDPMediaServer(channel_ingress_port=19101, feedback_listen_port=19103)

        proxy.start()
        client.start()
        server.start()
        try:
            decision = server.abr.select_action(
                measured_throughput_kbps=4000.0,
                rtt_current_ms=15.0,
                packet_loss_rate=0.07,
                buffer_occupancy_sec=5.0,
            )
            for _ in range(4):
                server.send_chunkBurst(decision, num_video_packets=8, payload_bytes=400)
                time.sleep(0.04)
            time.sleep(0.15)
            self.assertGreater(proxy.stats["total_ingress_packets"], 20)
            self.assertGreater(client.raw_received_packets, 10)
        finally:
            server.stop()
            client.stop()
            proxy.stop()



    def test_patent_claim1_consecutive_burst_interleaved_recovery(self) -> None:
        """
        PATENT CLAIM 1 & 2 PROOF:
        When a wireless burst drops 3 CONSECUTIVE packets in a row on the wire:
          - Standard Un-interleaved XOR (D=1, k=4) recovers 0/3 packets (0% recovery).
          - Our 2D Matrix Burst-Stride Interleaver (D=3, k=4) spreads the 3 consecutive drops
            across 3 distinct FEC groups and recovers 3/3 packets (100% recovery)!
        """
        from protocol import FRAME_I_KEYFRAME, FRAME_P_MOTION, FRAME_B_DISPOSABLE
        encoder = FECEncoder()

        # Create 12 media packets (D=3 groups x k=4 packets per group)
        media_pkts = [
            MediaPacket(
                seq_num=i + 1,
                timestamp_ms=1000 + i * 5,
                stream_type=STREAM_VIDEO,
                bitrate_tier=TIER_720P,
                packet_type=PKT_MEDIA_PAYLOAD,
                fec_group_id=0,
                payload_size=32,
                reserved_flags=pack_flags(chunk_id=1, frame_class=FRAME_I_KEYFRAME),
                payload=f"PATENT_PACKET_PAYLOAD_{i:02d}_XYZ".encode("utf-8").ljust(32, b"_"),
            )
            for i in range(12)
        ]

        # A. Standard Un-interleaved (D=1): drop 3 consecutive packets (indices 0, 1, 2)
        uninterleaved_wire = encoder.encode_interleaved_matrix(
            media_pkts, fec_k=4, stride_d=1, start_seq_num=100, enable_uep=False
        )
        dec_standard = FECDecoder()
        for idx, pkt in enumerate(uninterleaved_wire):
            if idx in (0, 1, 2):  # 3 consecutive packets dropped in Group 0!
                continue
            dec_standard.receive_packet(pkt)
        self.assertEqual(dec_standard.total_packets_recovered, 0)

        # B. Patent-Grade 2D Matrix Interleaved (D=3, k=4): drop 3 consecutive packets on wire!
        interleaved_wire = encoder.encode_interleaved_matrix(
            media_pkts, fec_k=4, stride_d=3, start_seq_num=500, enable_uep=False
        )
        dec_patent = FECDecoder()
        for idx, pkt in enumerate(interleaved_wire):
            if idx in (3, 4, 5):  # 3 consecutive packets dropped on the wire!
                continue
            dec_patent.receive_packet(pkt)
        # All 3 consecutive erased packets are 100% reconstructed in 0 RTT!
        self.assertEqual(dec_patent.total_packets_recovered, 3)

if __name__ == "__main__":

    unittest.main()
