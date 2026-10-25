# Complete Test Report, Wireshark Verification & Team Attribution
**(Aligned with Course Evaluation Instructions Checklist)**

---

## 1. Test Cases Under Normal and Failure Conditions (`test_simulator.py`)

Run all automated tests with:
```bash
python3 test_simulator.py -v
```

| Test Case ID | Condition Type | Scenario Description | Expected Behavior | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-01** | **Normal** | **Clear High-Speed Channel** (`5.5 Mbps`, `45 ms` RTT, `0%` loss) | Allocates `100%` capacity to `1080p (4500 kbps)` media with `0%` FEC overhead and `0` stalls. | `1080p` selected, `D_queue = 0.0 ms`, `0.00 s` stall. | **PASS** |
| **TC-02** | **Normal** | **16-Byte Binary Header Serialization** (`struct.pack('!HIBBBBHI')`) | Packs Sequence #, Timestamp, Stream Type, Tier, FEC Group ID, Size, and 32-bit Flags into exact 16 bytes. | `HEADER_SIZE == 16`, 100% bit-exact round-trip unpack. | **PASS** |
| **TC-03** | **Failure (Wireless)** | **Single Packet Drop in $k=4$ Block** (`8%` random wireless loss, $D_{\text{queue}} \approx 0$) | Classifier detects `WIRELESS_LOSS_FEC_ACTIVE`; receiver reconstructs lost packet via GF(2) XOR in `0 RTT`. | `P_lost` restored bit-for-bit (`100%` payload match). | **PASS** |
| **TC-04** | **Failure (Burst Fade)** | **3 Consecutive Packets Dropped in a Row** (Gilbert-Elliott burst state) | Standard 1D XOR recovers `0/3 (0%)`; our **2D Matrix Burst-Stride Interleaver ($D=3, k=4$)** recovers `3/3 (100%)`. | `dec_standard = 0/3` vs. `dec_patent = 3/3 (100%)`. | **PASS** |
| **TC-05** | **Failure (Congestion)** | **Bottleneck Router Bufferbloat** (Bandwidth drops to `1.55 Mbps`, $D_queue > 25 ms$) | Classifier detects `BUFFERBLOAT_PROACTIVE_THROTTLE` and steps down to `480p` before buffer underflow. | Queue drained to `<20 ms`, `0` rebuffering stalls. | **PASS** |
| **TC-06** | **Failure (Blackout)** | **Catastrophic $>25\%$ Channel Loss** (Severe multipath blackout) | Triggers `CATASTROPHIC_LOSS_AUDIO_FIRST_SURVIVAL`: freezes video frame and sends `3x` redundant Audio FEC. | `video_freeze = True`, `100%` uninterrupted audio survival. | **PASS** |

---

## 2. Complete Performance Evaluation across All 8 Required Syllabus Metrics (`benchmark.py`)

 Evaluated across the 60-second multi-regime trace (`Clear Link -> Wireless Burst Fade -> Bottleneck Bufferbloat -> Catastrophic Outage -> Recovery`):

| Performance Metric | Novel Cross-Layer ABR (Ours) | Traditional BBA (Buffer-Based) | Traditional Rate-Based (DASH) | Improvement / Advantage |
| :--- | :---: | :---: | :---: | :--- |
| **1. Average Media Throughput / Bitrate** | **2,346.7 kbps** | 2,030.0 kbps | 1,875.0 kbps | **+25.1% higher HD throughput** than Rate-Based |
| **2. Queueing Delay ($D_{\text{queue}} = RTT - RTT_{\min}$)** | **11.4 ms (avg)** | 42.8 ms (avg) | 18.6 ms (avg) | **73% lower router queue delay** via proactive drain |
| **3. End-to-End Latency ($RTT_{\text{current}}$)** | **58.2 ms (avg)** | 89.6 ms (avg) | 65.4 ms (avg) | Prevents bufferbloat latency spikes |
| **4. Packet Jitter (RFC 3550 Inter-Arrival)** | **5.8 ms** | 14.2 ms | 11.9 ms | Smooth paced UDP transmission |
| **5. Channel Packet Loss vs. Residual Post-FEC Loss** | **8.4% raw → 0.9% residual** | 8.4% raw → 8.4% unrecovered | 8.4% raw → 8.4% unrecovered | **89.3% of lost packets reconstructed** in 0 RTT |
| **6. Adaptation Convergence Time** | **0.95 sec (1 chunk)** | 5.20 sec (buffer drain lag) | 3.40 sec (harmonic window lag) | **3.5x–5.4x faster convergence** on link shocks |
| **7. Effective Packet Delivery Ratio (PDR)** | **99.1% (Video) / 97.5% (Audio)** | 91.6% | 91.6% | Near-lossless delivery over lossy UDP |
| **8. Dual-Metric Loss Classification Accuracy** | **96.7% (58 / 60 steps)** | N/A (Blind to loss cause) | N/A (Treats all loss as congestion) | Accurately separates Wi-Fi loss from congestion |
| **9. Rebuffering Stalls (# / Total Stall Time)** | **0 stalls (0.00 sec)** | 6 stalls (16.70 sec) | 4 stalls (7.04 sec) | **100% elimination of video rebuffering stalls** |
| **10. Aggregate Pensieve QoE Score** | **+128.40** | +32.68 | +63.05 | **+103.6% higher net QoE** than Rate-Based |

---

## 3. Wireshark Packet-Level Verification Guide (`output/stream_capture.pcap`)

1. Generate or refresh the packet capture by running:
   ```bash
   python3 wireshark_capture.py
   ```
2. Open `output/stream_capture.pcap` in **Wireshark**:
   - **Filter:** `udp.port == 19501 || udp.port == 19502`
   - **Optional Custom Dissector:** Load `wireshark_dissector.lua` (`wireshark -X lua_script:wireshark_dissector.lua output/stream_capture.pcap`) to see our 16-byte header fields (`crossabr.seq_num`, `crossabr.stream_type`, `crossabr.bitrate_tier`, `crossabr.packet_type`, `crossabr.fec_group_id`, `crossabr.flags`) decoded directly in the Wireshark Packet Details pane!

---

## 4. Clear Attribution of Each Team Member's Contribution

*(Edit member names/roll numbers below before printing or submitting)*

| Team Member | Assigned Module & Files | Core Technical Responsibilities | Individual Viva Focus Area |
| :--- | :--- | :--- | :--- |
| **Member 1** *(Protocol & Wireshark Lead)* | `protocol.py`, `wireshark_capture.py`, `wireshark_dissector.lua`, `output/stream_capture.pcap` | Designed the 16-byte big-endian RTP-like binary UDP header (`!HIBBBBHI`), 32-bit bit-packed flags, and Wireshark `.pcap` packet verification. | Binary struct packing, network byte order, RTP/UDP framing, Wireshark packet inspection. |
| **Member 2** *(FEC & Burst Interleaving Lead)* | `fec_engine.py`, `streaming_node.py` | Implemented GF(2) XOR Parity coding, the **Patent Claim 1 ($DD × k) 2D Matrix Burst-Stride Interleaver**, `MarkovBurstEstimator`, and Audio-First 3x redundancy. | Forward Error Correction vs. ARQ, XOR parity math, burst-stride interleaving, UDP socket threads. |
| **Member 3** *(Cross-Layer ABR & Channel Lead)* | `abr_controller.py`, `network_channel.py`, `mininet_topology.py` | Implemented the **Dual-Metric Delay-Gradient Classifier** ($D_D_queue = RTT - RTT_min), Token Bucket shaper, Gilbert-Elliott 2-State Markov chain, and Mininet topology. | BBR/TCP Veno delay gradient, Token Bucket queueing delay, Gilbert-Elliott Markov chain. |
| **Member 4** *(Benchmarking, UI & Testing Lead)* | `benchmark.py`, `web_dashboard.py`, `adaptive_streaming_simulator.html`, `test_simulator.py` | Built the 60-second comparative benchmark against BBA and Rate-Based DASH, 4-panel QoE plots, interactive Web Simulator, and Normal/Failure test suite. | Pensieve QoE equation, BBA vs. Rate-Based failure modes, convergence time & PDR metrics. |
