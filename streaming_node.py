"""
streaming_node.py — End-to-End Raw UDP Socket Media Streaming Server & Client
==============================================================================
Implements real UDP socket streaming (`socket.AF_INET`, `socket.SOCK_DGRAM`) using the
16-byte binary header (`protocol.py`), dynamic XOR parity FEC (`fec_engine.py`), and
cross-layer RTCP-like feedback loop.
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
import socket
import threading
import time
from typing import Dict, List, Optional
from abr_controller import ABRDecision, CrossLayerDelayGradientABR
from fec_engine import FECDecoder, FECEncoder
from protocol import (
    FeedbackPacket,
    MediaPacket,
    PKT_MEDIA_PAYLOAD,
    STREAM_AUDIO,
    STREAM_VIDEO,
    TIER_1080P,
    current_time_ms,
    pack_flags,
)


class UDPMediaClient:
    """
    Receiver node listening on a raw UDP socket.
    - Unpacks 16-byte RTP-like headers
    - Executes on-the-fly XOR Parity FEC recovery (`FECDecoder`)
    - Tracks separate Audio and Video continuity and client playback buffer occupancy
    - Emits RTCP-like `FeedbackPacket` reports back to the server UDP socket
    """

    def __init__(self, listen_port: int, server_feedback_port: int) -> None:
        self.listen_port = listen_port
        self.server_feedback_port = server_feedback_port
        self.fec_decoder = FECDecoder()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.listen_port))
        self.sock.settimeout(0.05)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self.highest_seq: int = -1
        self.expected_packets: int = 0
        self.raw_received_packets: int = 0
        self.buffer_sec: float = 4.0
        self.last_jitter_ms: float = 0.0
        self._prev_transit_ms: Optional[float] = None
        self.recent_headers: List[Dict[str, object]] = []

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self.sock.close()

    def _rx_loop(self) -> None:
        while self._running:
            try:
                raw_bytes, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                pkt = MediaPacket.from_bytes(raw_bytes)
            except ValueError:
                continue

            now_ms = current_time_ms()
            transit = float((now_ms - pkt.timestamp_ms) & 0xFFFFFFFF)
            if self._prev_transit_ms is not None:
                d = abs(transit - self._prev_transit_ms)
                self.last_jitter_ms += (d - self.last_jitter_ms) / 16.0
            self._prev_transit_ms = transit

            with self._lock:
                self.raw_received_packets += 1
                if self.highest_seq < 0:
                    self.highest_seq = pkt.seq_num
                    self.expected_packets = 1
                else:
                    delta = (pkt.seq_num - self.highest_seq) & 0xFFFF
                    if 0 < delta < 32768:
                        self.expected_packets += delta
                        self.highest_seq = pkt.seq_num

                delivered, reconstructed = self.fec_decoder.receive_packet(pkt)
                if len(self.recent_headers) < 25:
                    self.recent_headers.append(pkt.summary_dict())
                if reconstructed is not None and len(self.recent_headers) < 25:
                    rec_summary = reconstructed.summary_dict()
                    rec_summary["reconstructed_by_xor_fec"] = True
                    self.recent_headers.append(rec_summary)

                # Send periodic feedback report every 5 packets
                if self.raw_received_packets % 5 == 0:
                    loss_rate = max(
                        0.0,
                        1.0 - (self.raw_received_packets / max(1, self.expected_packets)),
                    )
                    fb = FeedbackPacket(
                        ack_seq=pkt.seq_num,
                        echo_timestamp_ms=pkt.timestamp_ms,
                        client_loss_rate=loss_rate,
                        client_jitter_ms=self.last_jitter_ms,
                        client_buffer_sec=self.buffer_sec,
                        fec_recovered_count=self.fec_decoder.total_packets_recovered,
                    )
                    try:
                        self.sock.sendto(
                            fb.to_bytes(), ("127.0.0.1", self.server_feedback_port)
                        )
                    except OSError:
                        pass


class UDPMediaServer:
    """
    Sender node transmitting audio and video packets over raw UDP sockets to the
    Network Channel Proxy (`channel_ingress_port`) and receiving RTCP-like feedback
    on `feedback_listen_port`.
    """

    def __init__(self, channel_ingress_port: int, feedback_listen_port: int) -> None:
        self.channel_ingress_port = channel_ingress_port
        self.feedback_listen_port = feedback_listen_port
        self.fec_encoder = FECEncoder()
        self.abr = CrossLayerDelayGradientABR()

        self.tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.fb_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.fb_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.fb_sock.bind(("127.0.0.1", self.feedback_listen_port))
        self.fb_sock.settimeout(0.05)

        self.seq_num: int = 0
        self.chunk_id: int = 0
        self.latest_rtt_ms: float = 50.0
        self.latest_loss_rate: float = 0.0
        self.latest_buffer_sec: float = 4.0
        self.feedback_received: int = 0

        self._running = False
        self._fb_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._fb_thread = threading.Thread(target=self._feedback_loop, daemon=True)
        self._fb_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._fb_thread and self._fb_thread.is_alive():
            self._fb_thread.join(timeout=0.5)
        self.tx_sock.close()
        self.fb_sock.close()

    def _feedback_loop(self) -> None:
        while self._running:
            try:
                raw_bytes, _ = self.fb_sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                fb = FeedbackPacket.from_bytes(raw_bytes)
            except ValueError:
                continue

            now_ms = current_time_ms()
            rtt = float((now_ms - fb.echo_timestamp_ms) & 0xFFFFFFFF)
            if 0 < rtt < 5000:
                self.latest_rtt_ms = rtt
            self.latest_loss_rate = fb.client_loss_rate
            self.latest_buffer_sec = fb.client_buffer_sec
            self.feedback_received += 1

    def send_chunkBurst(
        self,
        decision: ABRDecision,
        num_video_packets: int = 8,
        payload_bytes: int = 600,
    ) -> int:
        """
        Transmits a multiplexed burst of Audio (`Stream Type = 0`) and Video (`Stream Type = 1`)
        UDP datagrams together with dynamic XOR Parity FEC packets according to `decision`.
        Returns total UDP packets sent.
        """
        self.chunk_id = (self.chunk_id + 1) & 0xFF
        packets_sent = 0

        # 1. Always transmit Audio Stream packets first (Audio-First Survival Priority)
        audio_group: List[MediaPacket] = []
        for r_idx in range(decision.audio_redundancy):
            self.seq_num = (self.seq_num + 1) & 0xFFFF
            audio_payload = (
                f"AUDIO_FRAME_CHUNK_{self.chunk_id}_COPY_{r_idx}".encode("utf-8").ljust(160, b"A")
            )
            audio_pkt = MediaPacket(
                seq_num=self.seq_num,
                timestamp_ms=current_time_ms(),
                stream_type=STREAM_AUDIO,
                bitrate_tier=decision.bitrate_tier,
                packet_type=PKT_MEDIA_PAYLOAD,
                fec_group_id=self.chunk_id,
                payload_size=len(audio_payload),
                reserved_flags=pack_flags(
                    fec_k=0,
                    fec_idx=r_idx,
                    chunk_id=self.chunk_id,
                    video_freeze=decision.video_freeze,
                    audio_redundant=(r_idx > 0),
                ),
                payload=audio_payload,
            )
            audio_group.append(audio_pkt)

        for apkt in audio_group:
            self.tx_sock.sendto(apkt.to_bytes(), ("127.0.0.1", self.channel_ingress_port))
            packets_sent += 1

        # If Audio-First Video Freeze is active (>20% catastrophic loss), skip heavy video packets
        if decision.video_freeze:
            return packets_sent

        # 2. Transmit Video Stream packets with Dynamic XOR Parity FEC blocks
        fec_k = decision.fec_k
        current_block: List[MediaPacket] = []

        for v_idx in range(num_video_packets):
            self.seq_num = (self.seq_num + 1) & 0xFFFF
            patternByte = bytes([(self.chunk_id + v_idx * 17) & 0xFF])
            video_payload = (
                f"VIDEO_CHUNK_{self.chunk_id}_PKT_{v_idx}_".encode("utf-8")
                + patternByte * max(32, payload_bytes - 24)
            )
            vpkt = MediaPacket(
                seq_num=self.seq_num,
                timestamp_ms=current_time_ms(),
                stream_type=STREAM_VIDEO,
                bitrate_tier=decision.bitrate_tier,
                packet_type=PKT_MEDIA_PAYLOAD,
                fec_group_id=0,
                payload_size=len(video_payload),
                reserved_flags=pack_flags(
                    fec_k=fec_k,
                    fec_idx=len(current_block),
                    chunk_id=self.chunk_id,
                    end_of_chunk=(v_idx == num_video_packets - 1),
                    video_freeze=False,
                ),
                payload=video_payload,
            )

            if fec_k > 0:
                current_block.append(vpkt)
                if len(current_block) == fec_k:
                    self.seq_num = (self.seq_num + 1) & 0xFFFF
                    tagged_media, parity_pkt = self.fec_encoder.encode_group(
                        current_block, next_seq_num=self.seq_num
                    )
                    for mpkt in tagged_media:
                        self.tx_sock.sendto(
                            mpkt.to_bytes(), ("127.0.0.1", self.channel_ingress_port)
                        )
                        packets_sent += 1
                    if parity_pkt is not None:
                        self.tx_sock.sendto(
                            parity_pkt.to_bytes(), ("127.0.0.1", self.channel_ingress_port)
                        )
                        packets_sent += 1
                    current_block = []
            else:
                self.tx_sock.sendto(vpkt.to_bytes(), ("127.0.0.1", self.channel_ingress_port))
                packets_sent += 1

        # Flush any remaining partial video block
        for mpkt in current_block:
            self.tx_sock.sendto(mpkt.to_bytes(), ("127.0.0.1", self.channel_ingress_port))
            packets_sent += 1

        return packets_sent
