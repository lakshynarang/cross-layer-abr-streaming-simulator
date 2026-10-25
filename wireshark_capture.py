"""
wireshark_capture.py — Wireshark Packet-Level PCAP Generator & Inspector
=========================================================================
Generates a standard libpcap (`.pcap`) capture file (`output/stream_capture.pcap`)
containing real Ethernet + IPv4 + UDP frames carrying our 16-byte custom RTP-like
binary header (`!HIBBBBHI`), Audio/Video media payloads, and 2D Matrix XOR Parity
FEC packets so the group can open `output/stream_capture.pcap` directly in Wireshark
for packet-level verification during the 5-minute demonstration.
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
import struct
import time
from typing import List
from fec_engine import FECEncoder
from protocol import (
    FRAME_B_DISPOSABLE,
    FRAME_I_KEYFRAME,
    FRAME_P_MOTION,
    MediaPacket,
    PKT_MEDIA_PAYLOAD,
    STREAM_AUDIO,
    STREAM_VIDEO,
    TIER_720P,
    pack_flags,
)


def _ipv4_checksum(header_bytes: bytes) -> int:
    if len(header_bytes) % 2 == 1:
        header_bytes += b"\x00"
    total = sum(struct.unpack(f"!{len(header_bytes)//2}H", header_bytes))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def build_ethernet_ipv4_udp_frame(
    udp_payload: bytes,
    src_ip: str = "10.0.0.1",
    dst_ip: str = "10.0.0.2",
    src_port: int = 19501,
    dst_port: int = 19502,
    ip_id: int = 1,
) -> bytes:
    """Constructs a complete IEEE 802.3 Ethernet + IPv4 + UDP frame for Wireshark inspection."""
    eth_hdr = struct.pack("!6s6sH", b"\x00\x00\x00\x00\x00\x02", b"\x00\x00\x00\x00\x00\x01", 0x0800)
    udp_len = 8 + len(udp_payload)
    udp_hdr = struct.pack("!HHHH", src_port, dst_port, udp_len, 0)

    ip_total_len = 20 + udp_len
    ip_hdr_no_csum = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0x00,
        ip_total_len,
        ip_id & 0xFFFF,
        0x4000,
        64,
        socket.IPPROTO_UDP,
        0,
        socket.inet_aton(src_ip),
        socket.inet_aton(dst_ip),
    )
    csum = _ipv4_checksum(ip_hdr_no_csum)
    ip_hdr = ip_hdr_no_csum[:10] + struct.pack("!H", csum) + ip_hdr_no_csum[12:]
    return eth_hdr + ip_hdr + udp_hdr + udp_payload


def generate_pcap_file(output_pcap_path: str) -> int:
    """Writes a libpcap file with Audio, I/P/B Video, and 2D Interleaved XOR Parity packets."""
    os.makedirs(os.path.dirname(os.path.abspath(output_pcap_path)), exist_ok=True)
    encoder = FECEncoder()

    # Global PCAP header (magic=0xa1b2c3d4, v2.4, snaplen=65535, linktype=1 Ethernet)
    pcap_global_hdr = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)

    raw_packets: List[MediaPacket] = []
    # 1. Add 2 Audio packets (Stream Type = 0)
    for a_idx in range(2):
        raw_packets.append(
            MediaPacket(
                seq_num=a_idx + 1,
                timestamp_ms=1000 + a_idx * 20,
                stream_type=STREAM_AUDIO,
                bitrate_tier=TIER_720P,
                packet_type=PKT_MEDIA_PAYLOAD,
                fec_group_id=0,
                payload_size=160,
                reserved_flags=pack_flags(
                    fec_k=0,
                    fec_idx=a_idx,
                    chunk_id=1,
                    audio_redundant=(a_idx == 1),
                    frame_class=FRAME_I_KEYFRAME,
                    stride_d=1,
                ),
                payload=f"OPUS_AUDIO_FRAME_{a_idx}_VOICE_SURVIVAL_STREAM".encode("utf-8").ljust(160, b"A"),
            )
        )

    # 2. Add 12 Video packets (I, P, B frames) and encode with Stride D=3, k=4 Matrix Interleaver
    video_input: List[MediaPacket] = []
    for v_idx in range(12):
        f_class = FRAME_I_KEYFRAME if v_idx < 4 else (FRAME_P_MOTION if v_idx < 10 else FRAME_B_DISPOSABLE)
        video_input.append(
            MediaPacket(
                seq_num=10 + v_idx,
                timestamp_ms=1040 + v_idx * 10,
                stream_type=STREAM_VIDEO,
                bitrate_tier=TIER_720P,
                packet_type=PKT_MEDIA_PAYLOAD,
                fec_group_id=0,
                payload_size=400,
                reserved_flags=pack_flags(
                    fec_k=4,
                    fec_idx=v_idx % 4,
                    chunk_id=1,
                    frame_class=f_class,
                    stride_d=3,
                ),
                payload=f"H264_VIDEO_NAL_SLICE_{v_idx:02d}_CLASS_{f_class}".encode("utf-8").ljust(400, b"V"),
            )
        )

    interleaved_video = encoder.encode_interleaved_matrix(
        video_input, fec_k=4, stride_d=3, start_seq_num=3, enable_uep=False
    )
    all_packets = raw_packets + interleaved_video

    base_ts = int(time.time())
    with open(output_pcap_path, "wb") as f:
        f.write(pcap_global_hdr)
        for idx, pkt in enumerate(all_packets):
            udp_bytes = pkt.to_bytes()
            eth_frame = build_ethernet_ipv4_udp_frame(
                udp_bytes,
                src_ip="10.0.0.1",
                dst_ip="10.0.0.2",
                src_port=19501,
                dst_port=19502,
                ip_id=100 + idx,
            )
            ts_sec = base_ts + (idx // 10)
            ts_usec = (idx % 10) * 100_000
            pkt_hdr = struct.pack("<IIII", ts_sec, ts_usec, len(eth_frame), len(eth_frame))
            f.write(pkt_hdr)
            f.write(eth_frame)

    return len(all_packets)


if __name__ == "__main__":
    out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "stream_capture.pcap")
    count = generate_pcap_file(out_file)
    print(f"Generated Wireshark PCAP capture ({count} packets) at: {out_file}")
