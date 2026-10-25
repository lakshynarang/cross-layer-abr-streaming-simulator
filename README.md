# Cross-Layer Delay-Gradient ABR with Dynamic FEC & Audio-First Survival

**Course:** Computer Networks Mini-Project Evaluation  
**Evaluator:** Dr. Swati  
**Problem Statement:** Adaptive Video/Audio Streaming Simulator — *Dynamically adapt transmission rate and media quality according to available bandwidth, queueing delay, and packet loss.*

## 1. Executive Summary & Core Technical Novelty

Conventional Adaptive Bitrate (ABR) streaming protocols—such as **MPEG-DASH**, **Apple HLS**, and **Buffer-Based Adaptation (BBA)**—operate strictly at the application layer over TCP/HTTP. Because they lack visibility into transport-layer queueing dynamics, they suffer from a fundamental theoretical flaw: **they treat all packet loss and throughput fluctuations as network congestion**. Consequently, a brief 100 ms wireless multipath fade or Wi-Fi interference burst causes traditional ABR controllers to catastrophically collapse video quality from `1080p` down to `240p`.

This project implements a **Cross-Layer Transport-Aware Adaptive Video/Audio Streaming Simulator** over **raw UDP sockets** with a custom **16-byte RTP-like binary header** (`struct.pack('!HIBBBBHI')`). It introduces three synergistic Computer Networks innovations:

1. **Dual-Metric Loss Classifier (Google BBR & TCP Veno Principle):**
   - Continuously tracks minimum propagation round-trip time ($RTT_{\min}$) and instantaneous RTT ($RTT_{\text{current}}$) to isolate bottleneck queueing delay:
     $$D_{\text{queue}}(t) = RTT_{\text{current}}(t) - RTT_{\min}$$
   - **Wireless / Random Channel Loss ($D_{\text{queue}} \approx 0$ during loss):** When packets drop while router queues are empty ($D_{\text{queue}} \le 25\text{ ms}$), the classifier identifies **non-congestive wireless loss**. Instead of panicking and slashing video resolution to `240p`, it preserves HD quality (`720p`) and activates **Dynamic XOR Parity Forward Error Correction (FEC)**.
   - **Bottleneck Bufferbloat Congestion ($D_{\text{queue}} > 25\text{ ms}$):** When router FIFO queues build up, the controller detects congestion via the rising delay gradient $\nabla D_{\text{queue}}$ *before* tail-drop loss occurs, proactively stepping down transmission rate to drain the bottleneck queue and prevent playback stalls.

2. **Joint Source-Channel Coding with Dynamic XOR Parity FEC (RFC 5109):**
   - Dynamically partitions available channel capacity $C$ between media payload ($B_{\text{media}}$) and Galois-Field GF(2) XOR parity packets ($B_{\text{fec}}$):
     $$C = B_{\text{media}} + B_{\text{fec}}$$
   - **0% Loss Regime:** Allocates **100% capacity to `1080p` media** (`0% FEC` overhead).
   - **5–10% Wireless Loss Regime:** Allocates **80% capacity to `720p` media and 20% to XOR Parity FEC** ($k=4$ media packets + $1$ parity packet per `fec_group_id`), enabling the client to reconstruct lost packets on-the-fly ($P_{\text{lost}} = P_{\text{FEC}} \oplus \bigoplus_{i \neq \text{lost}} P_i$) with **zero TCP retransmission latency**.

3. **Audio-First Graceful Degradation (Psychoacoustic Survival):**
   - Multiplexes independent **Audio (`Stream Type = 0`)** and **Video (`Stream Type = 1`)** packet streams over UDP.
   - Under **catastrophic channel loss ($>20\%$)**, the transmitter intentionally freezes video frame updates (`FLAG_VIDEO_FREEZE = 1`) and reallocates bandwidth to **3x redundant Audio FEC duplication**, guaranteeing **100% uninterrupted audio intelligibility** during severe network blackouts.

## 2. Repository Structure

```text
cross_layer_abr_simulator/
├── README.md                           # Project overview, mathematical formulation & quickstart
├── requirements.txt                    # Project dependencies (matplotlib, python-pptx, python-docx)
├── protocol.py                         # 16-byte binary UDP header (`!HIBBBBHI`) & RTCP feedback struct
├── fec_engine.py                       # RFC 5109 XOR Parity Block FEC encoder & 2D Matrix Interleaver
├── network_channel.py                  # Intermediate UDP proxy: Token Bucket, FIFO queue, Jitter & Gilbert-Elliott Markov loss
├── abr_controller.py                   # Novel Cross-Layer Delay-Gradient ABR + BBA + Rate-Based baselines
├── streaming_node.py                   # Multi-threaded Raw UDP Socket Media Server & Client
├── benchmark.py                        # Single-command comparative evaluator & 4-panel QoE plotter
├── web_dashboard.py                    # Single-command local interactive web simulator server (port 8080)
├── adaptive_streaming_simulator.html   # Standalone interactive browser simulator, 16B inspector & XOR FEC lab
├── test_simulator.py                   # Automated unit & live UDP socket integration test suite
├── mininet_topology.py                 # Mininet Dumbbell Topology with fallback to UDP socket proxy
├── wireshark_capture.py                # Loopback PCAP packet capture generator
├── wireshark_dissector.lua             # Custom Wireshark Lua protocol dissector plugin
├── generate_slide_diagrams.py          # PNG diagram generator for academic presentation slides
├── generate_presentation.py            # Automated PowerPoint slide deck generator
├── MiniProject_Presentation_CSE20110.pptx # Final University PPT presentation (8 slides)
├── docs/
│   ├── MASTER_PROJECT_CONTEXT.md       # Comprehensive master technical blueprint & single source of truth
│   ├── Computer_Networks_Mini_Project_Report.docx # Complete academic mini-project report
│   ├── MiniProject_Presentation_CSE20110.pptx     # Final evaluation presentation slide deck
│   ├── architecture.md                 # System architecture, ASCII socket topology & message formats
│   ├── review_guide.md                 # Defense & viva guide for Dr. Swati (pitch, syllabus map, demo, Q&A)
│   ├── test_report.md                  # Test execution report & member contribution matrix
│   ├── patent_draft_indian_ipo.md      # Provisional patent specification draft
│   └── explain_like_im_5_brag_guide.pdf# Intuitive executive briefing guide
└── output/
    ├── benchmark_comparison.png        # 4-panel publication-grade QoE evaluation figure
    ├── benchmark_metrics.json          # Exported quantitative telemetry from benchmark runs
    └── stream_capture.pcap             # Wireshark-compatible packet capture trace
```

## 3. Quickstart & Execution Instructions

### A. Run the Comparative Benchmark & Generate the 4-Panel QoE Plot
```bash
python3 benchmark.py
```

### B. Launch the Interactive Real-Time Web Simulator
```bash
python3 web_dashboard.py
# Open http://127.0.0.1:8080 in your browser
```

### C. Run Automated Unit & Socket Verification Tests
```bash
python3 test_simulator.py -v
```

### D. Generate Wireshark Packet Trace & Inspect with Lua Dissector
```bash
python3 wireshark_capture.py
wireshark -X lua_script:wireshark_dissector.lua output/stream_capture.pcap
```

### E. Run Mininet Dumbbell Topology (or Localhost Standalone Fallback)
```bash
python3 mininet_topology.py
```

### F. Regenerate Presentation Slide Deck
```bash
python3 generate_slide_diagrams.py
python3 generate_presentation.py
```

## 4. Grounding References
- **Pensieve ABR & QoE Formulation:** Mao et al., *Neural Adaptive Video Streaming with Pensieve*, ACM SIGCOMM 2017 (`https://github.com/hongzimao/pensieve`).
- **Buffer-Based Adaptation (BBA):** Huang et al., *A Buffer-Based Approach to Rate Adaptation*, ACM SIGCOMM 2014.
- **TCP Veno (Wireless vs. Congestive Loss):** Fu & Liew, *TCP Veno: TCP Enhancement for Transmission over Wireless Access Networks*, IEEE JSAC 2003.
- **Google BBR (Delay-Gradient Control):** Cardwell et al., *BBR: Congestion-Based Congestion Control*, ACM Queue 2017.
- **RTP & Generic Forward Error Correction:** IETF RFC 3550 (RTP/RTCP) & IETF RFC 5109 (RTP Payload Format for Generic FEC).

---

## 5. Course Submission Checklist Mapping (All 12 Required Items)

| Course Instruction Requirement | Included Deliverable / File in This Repository |
| :--- | :--- |
| **1. Python, Mininet, Wireshark, Flask & Visualization** | `mininet_topology.py`, `wireshark_capture.py`, `web_dashboard.py`, `benchmark.py` |
| **2. Problem Statement and Objectives** | `README.md` (Section 1) & `docs/review_guide.md` |
| **3. Network Architecture & Dumbbell Topology** | `docs/architecture.md` (ASCII Thread & Socket Topology) & `mininet_topology.py` |
| **4. Protocol / Message-Format Design** | `protocol.py` (16-Byte Binary Header `!HIBBBBHI` + 32B RTCP Feedback Packet) |
| **5. Working Implementation & Interactive Simulation** | `streaming_node.py`, `web_dashboard.py`, `adaptive_streaming_simulator.html` |
| **6. Test Cases Under Normal & Failure Conditions** | `test_simulator.py` (5 automated test suites) & `docs/test_report.md` (TC-01 to TC-06) |
| **7. Performance Results (Delay, Throughput, Loss, Latency, Jitter, Convergence, PDR, Accuracy)** | `benchmark.py`, `output/benchmark_comparison.png`, `docs/test_report.md` (Section 2) |
| **8. Source Code and README** | Complete modular Python codebase + `README.md` |
| **9. Five-Minute Demonstration Script** | `docs/review_guide.md` & `explain_like_im_5_brag_guide.pdf` |
| **10. Individual Viva Preparation** | `docs/review_guide.md` (5 Tough Viva Q&As) & `docs/test_report.md` (Per-Member Viva Topics) |
| **11. Wireshark Packet-Level Verification** | `output/stream_capture.pcap`, `wireshark_capture.py`, `wireshark_dissector.lua` |
| **12. Clear Attribution of Each Team Member's Contribution** | `docs/test_report.md` (Section 4 — 4-Member Role & Viva Matrix) |
