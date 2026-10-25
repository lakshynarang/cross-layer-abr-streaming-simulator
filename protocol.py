"""
protocol.py — Custom 16-Byte RTP-Like Binary Packet Header & Cross-Layer Feedback Protocol
==========================================================================================
Implements RFC 3550 (RTP/RTCP) and RFC 5109 (Generic FEC) inspired transport framing
over raw UDP sockets using big-endian network byte order (`struct.pack('!HIBBBBHI')`),
extended with two patent-grade cross-layer innovations:
  1. 2-Bit Frame Importance Class (`FRAME_I_KEYFRAME`, `FRAME_P_MOTION`, `FRAME_B_DISPOSABLE`)
     for Content-Aware Unequal Error Protection (UEP).
  2. Closed-Loop Burst-Stride Interleaving Depth `D` (`stride_d` in 1..4) carried in the
     32-bit `reserved_flags` word and receiver RTCP feedback report.
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

import struct
import time
from dataclasses import dataclass
from typing import Dict

# Network byte-order (big-endian) 16-byte struct format string
HEADER_FORMAT = "!HIBBBBHI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
assert HEADER_SIZE == 16, f"Expected 16-byte header, got {HEADER_SIZE}"

# Extended RTCP-like Receiver Feedback Packet Format (32 bytes, big-endian)
# (ack_seq: I, echo_ts_ms: I, loss_rate: f, jitter_ms: f, buffer_sec: f,
#  fec_recovered_cnt: I, max_burst_len: H, recommended_stride_d: H)
FEEDBACK_FORMAT = "!IIfffIHH"
FEEDBACK_SIZE = struct.calcsize(FEEDBACK_FORMAT)

# Stream Type Constants (1B)
STREAM_AUDIO = 0
STREAM_VIDEO = 1

STREAM_NAMES: Dict[int, str] = {
    STREAM_AUDIO: "AUDIO",
    STREAM_VIDEO: "VIDEO",
}

# Bitrate Tier Constants (1B)
TIER_1080P = 0
TIER_720P = 1
TIER_480P = 2
TIER_240P = 3

BITRATE_TIERS_KBPS: Dict[int, int] = {
    TIER_1080P: 4500,
    TIER_720P: 2500,
    TIER_480P: 1200,
    TIER_240P: 400,
}

TIER_LABELS: Dict[int, str] = {
    TIER_1080P: "1080p (4500 kbps)",
    TIER_720P: "720p (2500 kbps)",
    TIER_480P: "480p (1200 kbps)",
    TIER_240P: "240p (400 kbps)",
}

AUDIO_BITRATE_KBPS = 64
MTU_PAYLOAD_BYTES = 1200

# Packet Type Constants (1B)
PKT_MEDIA_PAYLOAD = 0
PKT_XOR_PARITY_FEC = 1

PACKET_TYPE_NAMES: Dict[int, str] = {
    PKT_MEDIA_PAYLOAD: "MEDIA_PAYLOAD",
    PKT_XOR_PARITY_FEC: "XOR_PARITY_FEC",
}

# Patent Claim 2: Video Frame Importance Classes for Unequal Error Protection (UEP)
FRAME_I_KEYFRAME = 0     # High-priority IDR/Keyframe (always FEC-protected under wireless fade)
FRAME_P_MOTION = 1       # Medium-priority Inter-frame motion vectors (protected under moderate/high fade)
FRAME_B_DISPOSABLE = 2   # Low-priority bi-directional filler frame (0% FEC overhead; skipped first)

FRAME_CLASS_NAMES: Dict[int, str] = {
    FRAME_I_KEYFRAME: "I_FRAME_KEY",
    FRAME_P_MOTION: "P_FRAME_MOTION",
    FRAME_B_DISPOSABLE: "B_FRAME_DISP",
}

# Reserved/Flags 32-bit Bitfield Encoding Masks:
# Bits 24..31 (8 bits) : FEC block size `k` (number of media packets per FEC group)
# Bits 16..23 (8 bits) : Index `idx` within FEC group (0..k-1 for media, k for parity)
# Bits 8..15  (8 bits) : Chunk ID mod 256
# Bits 5..7   (3 bits) : Interleaving Stride Depth `stride_d` (1..7)
# Bits 3..4   (2 bits) : Frame Importance Class (0=I-Frame, 1=P-Frame, 2=B-Frame)
# Bit  2      (1 bit)  : Audio-First Redundant Duplicate Flag
# Bit  1      (1 bit)  : Video Freeze Active Flag
# Bit  0      (1 bit)  : End-of-Chunk Marker (M bit in RTP)
FLAG_END_OF_CHUNK = 1 << 0
FLAG_VIDEO_FREEZE = 1 << 1
FLAG_AUDIO_REDUNDANT = 1 << 2


def pack_flags(
    fec_k: int = 0,
    fec_idx: int = 0,
    chunk_id: int = 0,
    end_of_chunk: bool = False,
    video_freeze: bool = False,
    audio_redundant: bool = False,
    frame_class: int = FRAME_I_KEYFRAME,
    stride_d: int = 1,
) -> int:
    """Packs cross-layer FEC, UEP frame class, and burst-stride interleaving metadata into 4B flags."""
    flags = (
        ((fec_k & 0xFF) << 24)
        | ((fec_idx & 0xFF) << 16)
        | ((chunk_id & 0xFF) << 8)
        | ((stride_d & 0x07) << 5)
        | ((frame_class & 0x03) << 3)
    )
    if end_of_chunk:
        flags |= FLAG_END_OF_CHUNK
    if video_freeze:
        flags |= FLAG_VIDEO_FREEZE
    if audio_redundant:
        flags |= FLAG_AUDIO_REDUNDANT
    return flags & 0xFFFFFFFF


def unpack_flags(flags: int) -> Dict[str, int | bool]:
    """Unpacks the 4-byte Reserved/Flags field into structured cross-layer metadata."""
    return {
        "fec_k": (flags >> 24) & 0xFF,
        "fec_idx": (flags >> 16) & 0xFF,
        "chunk_id": (flags >> 8) & 0xFF,
        "stride_d": max(1, (flags >> 5) & 0x07),
        "frame_class": (flags >> 3) & 0x03,
        "end_of_chunk": bool(flags & FLAG_END_OF_CHUNK),
        "video_freeze": bool(flags & FLAG_VIDEO_FREEZE),
        "audio_redundant": bool(flags & FLAG_AUDIO_REDUNDANT),
    }


@dataclass
class MediaPacket:
    """Represents an RTP-like transport packet with a 16-byte binary header and binary payload."""
    seq_num: int
    timestamp_ms: int
    stream_type: int
    bitrate_tier: int
    packet_type: int
    fec_group_id: int
    payload_size: int
    reserved_flags: int
    payload: bytes = b""

    def to_bytes(self) -> bytes:
        header = struct.pack(
            HEADER_FORMAT,
            self.seq_num & 0xFFFF,
            self.timestamp_ms & 0xFFFFFFFF,
            self.stream_type & 0xFF,
            self.bitrate_tier & 0xFF,
            self.packet_type & 0xFF,
            self.fec_group_id & 0xFF,
            self.payload_size & 0xFFFF,
            self.reserved_flags & 0xFFFFFFFF,
        )
        return header + self.payload

    @classmethod
    def from_bytes(cls, raw_bytes: bytes) -> "MediaPacket":
        if len(raw_bytes) < HEADER_SIZE:
            raise ValueError(f"Packet too short ({len(raw_bytes)}B < {HEADER_SIZE}B header)")
        header_tuple = struct.unpack(HEADER_FORMAT, raw_bytes[:HEADER_SIZE])
        payload = raw_bytes[HEADER_SIZE:]
        return cls(
            seq_num=header_tuple[0],
            timestamp_ms=header_tuple[1],
            stream_type=header_tuple[2],
            bitrate_tier=header_tuple[3],
            packet_type=header_tuple[4],
            fec_group_id=header_tuple[5],
            payload_size=header_tuple[6],
            reserved_flags=header_tuple[7],
            payload=payload,
        )

    def header_hex_dump(self) -> str:
        hdr = self.to_bytes()[:HEADER_SIZE]
        return " ".join(f"{b:02X}" for b in hdr)

    def summary_dict(self) -> Dict[str, object]:
        meta = unpack_flags(self.reserved_flags)
        return {
            "seq_num": self.seq_num,
            "timestamp_ms": self.timestamp_ms,
            "stream_type": STREAM_NAMES.get(self.stream_type, f"UNKNOWN({self.stream_type})"),
            "bitrate_tier": TIER_LABELS.get(self.bitrate_tier, f"TIER({self.bitrate_tier})"),
            "packet_type": PACKET_TYPE_NAMES.get(self.packet_type, f"TYPE({self.packet_type})"),
            "fec_group_id": self.fec_group_id,
            "payload_size": self.payload_size,
            "fec_k": meta["fec_k"],
            "fec_idx": meta["fec_idx"],
            "stride_d": meta["stride_d"],
            "frame_class": FRAME_CLASS_NAMES.get(int(meta["frame_class"]), "I_FRAME"),
            "video_freeze": meta["video_freeze"],
            "audio_redundant": meta["audio_redundant"],
            "header_hex": self.header_hex_dump(),
        }


@dataclass
class FeedbackPacket:
    """RTCP-like receiver feedback report with closed-loop Markov burst-length telemetry."""
    ack_seq: int
    echo_timestamp_ms: int
    client_loss_rate: float
    client_jitter_ms: float
    client_buffer_sec: float
    fec_recovered_count: int
    max_observed_burst_len: int = 1
    recommended_stride_d: int = 1

    def to_bytes(self) -> bytes:
        return struct.pack(
            FEEDBACK_FORMAT,
            self.ack_seq & 0xFFFFFFFF,
            self.echo_timestamp_ms & 0xFFFFFFFF,
            float(self.client_loss_rate),
            float(self.client_jitter_ms),
            float(self.client_buffer_sec),
            self.fec_recovered_count & 0xFFFFFFFF,
            self.max_observed_burst_len & 0xFFFF,
            self.recommended_stride_d & 0xFFFF,
        )

    @classmethod
    def from_bytes(cls, raw_bytes: bytes) -> "FeedbackPacket":
        if len(raw_bytes) < FEEDBACK_SIZE:
            raise ValueError(f"Feedback packet too short ({len(raw_bytes)}B)")
        unpacked = struct.unpack(FEEDBACK_FORMAT, raw_bytes[:FEEDBACK_SIZE])
        return cls(
            ack_seq=unpacked[0],
            echo_timestamp_ms=unpacked[1],
            client_loss_rate=unpacked[2],
            client_jitter_ms=unpacked[3],
            client_buffer_sec=unpacked[4],
            fec_recovered_count=unpacked[5],
            max_observed_burst_len=unpacked[6],
            recommended_stride_d=unpacked[7],
        )


def current_time_ms() -> int:
    return int(time.monotonic() * 1000) & 0xFFFFFFFF
