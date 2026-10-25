# Low-Level System Architecture & Protocol Specification

## 1. End-to-End Multi-Threaded Data & Control Plane Architecture

The simulator decouples **media packetization & cross-layer control** (`UDPMediaServer`), **physical/link/network impairment emulation** (`UDPNetworkChannelProxy`), and **FEC reconstruction & playout buffering** (`UDPMediaClient`) across dedicated POSIX/Python threads communicating over non-blocking localhost UDP datagram sockets (`socket.AF_INET`, `socket.SOCK_DGRAM`).

```text
+---------------------------------------------------------------------------------------------------+
|                                   SENDER NODE (UDPMediaServer)                                    |
|                                                                                                   |
|  +-----------------------------+      +--------------------------------------------------------+  |
|  | CrossLayerDelayGradientABR  |      | Joint Source-Channel Packetizer & FECEncoder           |  |
|  | - Tracks RTT_min & RTT_curr |----->| - Stream 0 (Audio): 64 kbps + 1x..3x FEC Redundancy    |  |
|  | - D_queue = RTT - RTT_min   |      | - Stream 1 (Video): 1080p/720p/480p/240p + GF(2) XOR   |  |
|  | - Dual-Metric Classifier    |      | - Packs 16-Byte Header: struct.pack('!HIBBBBHI', ...)  |  |
|  +-----------------------------+      +---------------------------+----------------------------+  |
|                 ^                                                 |                               |
|                 | RTCP-like FeedbackPacket (24B)                  | Raw UDP Datagram (Header+Pay) |
|                 | socket.recvfrom(:19503)                         v socket.sendto(:19501)         |
+-----------------|-------------------------------------------------|-------------------------------+
                  |                                                 |
                  |                                                 v
                  |             +-------------------------------------------------------------------+
                  |             |            NETWORK CHANNEL EMULATOR (network_channel.py)          |
                  |             |                                                                   |
                  |             |  [Ingress Thread] ---> [Token Bucket Shaper (200Kbps..10Mbps)]    |
                  |             |                              |                                    |
                  |             |                              v                                    |
                  |             |                        [Bottleneck FIFO Router Queue]             |
                  |             |                         - Computes D_queue = Q_bytes / Rate       |
                  |             |                         - Tail-Drop if D_queue > max_queue_ms     |
                  |             |                              |                                    |
                  |             |                              v                                    |
                  |             |                        [Loss Engine: Uniform OR Gilbert-Elliott]  |
                  |             |                         - 2-State Markov: GOOD (0) <-> BAD (1)    |
                  |             |                              |                                    |
                  |             |                              v                                    |
                  |             |  [Egress Min-Heap] <-- [Delay + Gaussian Jitter N(d_prop, sigma)] |
                  |             +-----------------------------------+-------------------------------+
                  |                                                 |
                  |                                                 | Surviving Delayed UDP Datagram
                  |                                                 v socket.sendto(:19502)
+-----------------|-------------------------------------------------|-------------------------------+
|                 |                                                 v                               |
|  +--------------+--------------+      +--------------------------------------------------------+  |
|  | RTCP Feedback Reporter      |      | Receiver Unpacker & XOR FECDecoder (fec_engine.py)     |  |
|  | - Echoes sender timestamp   |<-----| - struct.unpack('!HIBBBBHI', raw[:16])                 |  |
|  | - Reports loss & jitter     |      | - Reconstructs lost packet: P_lost = P_fec ^ (^ P_i)   |  |
|  | - Reports buffer_sec        |      | - Separates Audio (Stream 0) & Video (Stream 1)        |  |
|  +-----------------------------+      +--------------------------------------------------------+  |
|                                                                                                   |
|                                   RECEIVER NODE (UDPMediaClient)                                  |
+---------------------------------------------------------------------------------------------------+
```

## 2. Binary Wire Format: 16-Byte RTP-Like Packet Header (`protocol.py`)

Every media and FEC parity datagram begins with an exact **16-byte binary header** serialized in network byte order (`!HIBBBBHI` in Python's `struct` module):

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|        Sequence Number        |         Timestamp (MSB)       |  Bytes 0..3
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Timestamp (LSB)       |  Stream Type  |  Bitrate Tier |  Bytes 4..7
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Packet Type  | FEC Group ID  |          Payload Size         |  Bytes 8..11
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   FEC_k (8b)  |  FEC_idx (8b) | Chunk_ID (8b) |0 0 0 0 0|A|F|M|  Bytes 12..15
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Variable-Length Payload                   |  Bytes 16..N
|                    (Media Frame Slice or XOR)                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Field-by-Field Specification:
| Byte Offset | Field Name | C / Python Type | Size | Encoding & Semantics |
| :--- | :--- | :--- | :---: | :--- |
| `0 .. 1` | `seq_num` | `uint16_t` (`H`) | 2 B | Monotonically increasing packet sequence number modulo $65536$. |
| `2 .. 5` | `timestamp_ms` | `uint32_t` (`I`) | 4 B | Monotonic sender clock in milliseconds for $RTT_{\text{current}}$ and jitter. |
| `6` | `stream_type` | `uint8_t` (`B`) | 1 B | `0` = Audio Stream (64 kbps), `1` = Video Stream. |
| `7` | `bitrate_tier` | `uint8_t` (`B`) | 1 B | `0` = 1080p (4500 kbps), `1` = 720p (2500 kbps), `2` = 480p (1200 kbps), `3` = 240p (400 kbps). |
| `8` | `packet_type` | `uint8_t` (`B`) | 1 B | `0` = Media Payload Packet, `1` = GF(2) XOR Parity FEC Packet. |
| `9` | `fec_group_id` | `uint8_t` (`B`) | 1 B | Block identifier (`0..255`) binding $k$ media packets and $1$ XOR parity packet. |
| `10 .. 11` | `payload_size` | `uint16_t` (`H`) | 2 B | Media byte length, or XOR sum of lengths ($\bigoplus_{i=0}^{k-1} \text{len}(P_i)$) for parity packets. |
| `12 .. 15` | `reserved_flags` | `uint32_t` (`I`) | 4 B | Bit-packed control word (`fec_k`, `fec_idx`, `chunk_id`, Audio Redundant `A`, Video Freeze `F`, Marker `M`). |

## 3. Mathematical Formulation of Core Algorithms

### A. Dual-Metric Loss Classifier (`abr_controller.py`)
$$RTT_{\min}(t) = \min_{0 \le \tau \le t} RTT(\tau), \qquad D_{\text{queue}}(t) = RTT(t) - RTT_{\min}(t)$$

- **Regime 1 — Clear Channel ($L < 3\%, D_{\text{queue}} \le 25\text{ ms}$):** Allocates 100% capacity to `1080p` media (`0% FEC`).
- **Regime 2 — Wireless Random/Burst Loss ($L \ge 3\%, D_{\text{queue}} \le 25\text{ ms}$):** Allocates 80% capacity to `720p` media and 20% to XOR Parity FEC ($k=4, r=1$).
- **Regime 3 — Bottleneck Bufferbloat Congestion ($D_{\text{queue}} > 25\text{ ms}$):** Proactively throttles bitrate before router FIFO tail-drop stalls occur.
- **Regime 4 — Catastrophic Outage ($L \ge 20\%$):** Triggers Audio-First Graceful Degradation (`FLAG_VIDEO_FREEZE = 1`, `3x` redundant audio packets).

### B. XOR Parity Erasure Coding (`fec_engine.py`)
$$P_{\text{FEC}} = P_0 \oplus P_1 \oplus \dots \oplus P_{k-1}, \qquad P_{\text{lost}} = P_{\text{FEC}} \oplus \bigoplus_{i \neq \text{lost}} P_i$$
