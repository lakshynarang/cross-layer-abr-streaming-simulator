# Cross-Layer Delay-Gradient ABR Streaming Simulator with Dynamic XOR FEC & Audio-First Survival

**Course:** Computer Networks  
**Institution:** MIT World Peace University, Pune  
**Project Type:** Computer Networks Mini Project  
**Evaluators:** Dr. Uma Pujeri and Dr. Swati

**Repository:** [GitHub — Cross-Layer ABR Streaming Simulator](https://github.com/lakshynarang/cross-layer-abr-streaming-simulator)

---

## 1. Project Overview

This project implements a Python-based adaptive audio/video streaming simulator designed to study streaming performance under unstable network conditions. It combines delay-gradient-based congestion awareness, Adaptive Bitrate (ABR) control, dynamic XOR-based Forward Error Correction (FEC), and audio-first graceful degradation.

Conventional adaptive streaming approaches often depend on throughput estimates or buffer occupancy to decide when to adjust video quality. These approaches may not always respond quickly to sudden changes in network conditions.

Our simulator explores a cross-layer approach in which changes in network delay help guide adaptation decisions, XOR-based redundancy supports packet-loss recovery, and audio is prioritized when network conditions become severe.

The project integrates protocol design, UDP communication, network simulation, adaptive streaming control, error recovery, testing, benchmarking, visualization, and packet analysis into a single experimental framework.

## 2. Project Objectives

- Implement UDP-based streaming communication using a custom RTP-like binary packet header.
- Monitor changes in network delay and use delay gradients to help identify congestion.
- Adapt streaming decisions according to simulated network conditions.
- Implement XOR-based Forward Error Correction to recover eligible packet losses.
- Explore interleaving to improve resilience against burst packet loss.
- Prioritize audio continuity during severe network degradation.
- Evaluate performance through benchmarking and comparison with baseline strategies.
- Visualize benchmark results and inspect network traffic using Wireshark.
- Support optional network-topology experiments using Mininet.

## 3. Key Innovations

### 3.1 Delay-Gradient-Based Congestion Awareness

The controller examines changes in network delay over time rather than relying exclusively on instantaneous throughput or buffer occupancy.

The delay gradient provides an additional signal for identifying potential congestion and guiding adaptive streaming decisions.

### 3.2 Dynamic XOR Forward Error Correction

XOR-based FEC introduces redundant information that can help recover certain lost packets without retransmission. The simulator explores adapting redundancy to network conditions and using interleaving to improve resilience against burst losses.

FEC recovery depends on the redundancy available and the pattern of packet losses.

### 3.3 Audio-First Graceful Degradation

During severe network degradation, maintaining audio continuity may be more useful than attempting to preserve high-quality video.

The simulator explores reducing or suspending video delivery while prioritizing audio and applying additional protection to improve continuity.

## 4. System Architecture

The simulator is organized into components that handle packet representation, adaptive control, error recovery, network behaviour, streaming execution, and performance evaluation.

```text
Streaming Source
      |
      v
Protocol / Packet Layer
      |
      v
Delay-Gradient ABR Controller
      |
      v
Dynamic XOR FEC and Interleaving
      |
      v
Network Channel Emulator
      |
      v
Streaming Receiver / Recovery
      |
      v
Benchmarking and Visualization
```

The architecture illustrates the main stages of the proposed streaming system.

### Packet Format

The project uses a custom 16-byte RTP-like binary header encoded using Python's `struct` module and network byte order.

The header format uses the following format string:

```python
struct.pack('!HIBBBBHI', ...)
```

The `!` indicates network byte order (big-endian). This is a project-specific RTP-like format and is not intended to imply complete compliance with the standard RTP protocol.

## 5. Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.10+ | Core simulator and supporting scripts |
| UDP sockets | Datagram-based communication |
| Python `struct` | Binary packet encoding and decoding |
| XOR-based FEC | Redundancy-based packet-loss recovery |
| Matplotlib | Benchmark visualization |
| HTML, CSS and JavaScript | Browser-based dashboard interface |
| Python `http.server` | Local dashboard server |
| Wireshark | Packet capture inspection |
| Lua | Custom Wireshark dissector |
| Mininet | Optional network-topology experiments |

## 6. Repository Structure

```text
cross-layer-abr-streaming-simulator/
│
├── protocol.py
├── abr_controller.py
├── fec_engine.py
├── network_channel.py
├── streaming_node.py
│
├── benchmark.py
├── test_simulator.py
├── web_dashboard.py
├── adaptive_streaming_simulator.html
│
├── mininet_topology.py
├── wireshark_capture.py
├── wireshark_dissector.lua
│
├── requirements.txt
├── README.md
├── .gitignore
│
├── benchmark_comparison.png
├── benchmark_metrics.json
├── stream_capture.pcap
│
├── output/
│   ├── benchmark_metrics.json
│   ├── benchmark_comparison.png
│   └── stream_capture.pcap
│
└── docs/
    ├── architecture.md
    └── test_report.md
```

### Main Files and Their Responsibilities

| File | Description |
|---|---|
| `protocol.py` | Packet format and protocol handling |
| `abr_controller.py` | Adaptive bitrate and congestion-control logic |
| `fec_engine.py` | XOR-based FEC and recovery logic |
| `network_channel.py` | Simulated network conditions and impairments |
| `streaming_node.py` | Streaming execution and communication |
| `benchmark.py` | Performance evaluation and baseline comparison |
| `test_simulator.py` | Test suite |
| `web_dashboard.py` | Local dashboard server |
| `adaptive_streaming_simulator.html` | Dashboard interface |
| `mininet_topology.py` | Mininet-based network experiments |
| `wireshark_capture.py` | Packet-capture workflow |
| `wireshark_dissector.lua` | Custom Wireshark dissector |
| `benchmark_comparison.png` | Benchmark comparison visualization |
| `benchmark_metrics.json` | Structured benchmark metrics |
| `stream_capture.pcap` | Packet-capture artifact |
| `docs/architecture.md` | Architecture documentation |
| `docs/test_report.md` | Test report documentation |
| `requirements.txt` | Python dependencies |

The benchmark and capture artifacts are available in the repository, including copies under `output/`.

## 7. Prerequisites

Before running the project, ensure the following are installed:

- **Python 3.10 or newer** — required for the core simulator.
- **pip** — Python package installer.
- **Git** — for cloning the repository.
- **A modern web browser** — for viewing the dashboard.

Additional tools are required for optional workflows:

- **Wireshark:** for inspecting packet captures and using the custom Lua dissector.
- **Mininet:** for network-topology experiments on a supported Linux environment.

## 8. Installation and Setup

Follow these steps to download and run the project.

### Step 1: Clone the Repository

Open a terminal or command prompt and execute:

```bash
git clone https://github.com/lakshynarang/cross-layer-abr-streaming-simulator.git
cd cross-layer-abr-streaming-simulator
```

Alternatively, download the repository as a ZIP file from GitHub, extract it, and open a terminal in the extracted project directory.

### Step 2: Install Dependencies

Install the required Python packages:

```bash
python -m pip install -r requirements.txt
```

If your system uses `python3`, execute:

```bash
python3 -m pip install -r requirements.txt
```

After installation, the environment is ready to run the core simulator and its supporting scripts.

## 9. Steps to Run the Project

Run the following commands from the repository's root directory.

### Step 1: Execute the Benchmark

```bash
python benchmark.py
```

This executes the benchmark workflow and evaluates the streaming approach against the available baseline strategies.

The project includes the following benchmark artifacts:

- `benchmark_metrics.json` — structured benchmark measurements.
- `benchmark_comparison.png` — visual comparison of benchmark results.

The `output/` directory also contains these result files. Open the generated visualization to compare performance and inspect the JSON file for the recorded metrics.

### Step 2: Launch the Web Dashboard

Start the dashboard server:

```bash
python web_dashboard.py
```

Open the following address in your web browser:

**http://127.0.0.1:8080**

The dashboard provides a browser-based interface for visualizing the simulator. Keep the terminal open while using it.

To stop the server, press `Ctrl+C` in the terminal.

### Step 3: Run the Test Suite

Execute:

```bash
python test_simulator.py -v
```

The test suite checks the simulator's implemented functionality. Review the terminal output to see the test results and identify any failures.

For additional testing documentation, see [`docs/test_report.md`](docs/test_report.md).

### Step 4: Inspect the Architecture

Open [`docs/architecture.md`](docs/architecture.md) to understand the system's design and component interactions.

This document complements the architecture overview provided in this README.

### Step 5: Review the Results

Inspect the benchmark artifacts:

- Open `benchmark_comparison.png` to view the performance comparison.
- Open `benchmark_metrics.json` to examine the recorded metrics.
- Check the corresponding files in `output/` when reviewing generated artifacts.

Use the latest benchmark results when preparing a demonstration or project report.

## 10. Wireshark Packet Analysis

The project includes a packet capture and a custom Lua dissector for inspecting the streaming protocol.

### Step 1: Locate the Packet Capture

The repository contains:

```text
stream_capture.pcap
```

A copy is also available at:

```text
output/stream_capture.pcap
```

### Step 2: Open the Capture in Wireshark

Open the capture from the terminal:

```bash
wireshark output/stream_capture.pcap
```

Alternatively, launch Wireshark manually and select **File → Open** to load the capture.

### Step 3: Load the Custom Dissector

The repository contains the custom dissector:

```text
wireshark_dissector.lua
```

Load the dissector when launching Wireshark:

```bash
wireshark -X lua_script:wireshark_dissector.lua output/stream_capture.pcap
```

The custom dissector is intended to help interpret the project's packet header and related fields.

### What to Observe

- Packet arrival timing and ordering.
- Header information decoded by the custom dissector.
- Traffic patterns under simulated network conditions.
- FEC-related traffic and recovery behaviour, where represented in the capture.
- Changes in transmission patterns during adaptive streaming.

Correlate packet-level observations with benchmark measurements and the test report for a more complete evaluation.

The repository also includes `wireshark_capture.py` for the packet-capture workflow.

## 11. Optional Mininet Experiments

The project includes `mininet_topology.py` for network-topology experiments using Mininet.

Mininet is optional and generally requires a supported Linux environment with the necessary permissions and dependencies.

On a configured Linux system, run:

```bash
sudo python3 mininet_topology.py
```

This workflow can be used to explore network behaviour in a topology-based environment. The core Python simulator, benchmark, and dashboard can be used independently of Mininet.

## 12. Performance Evaluation

The project evaluates streaming behaviour under simulated network conditions and compares the proposed approach with available baseline strategies.

Relevant metrics include:

- Number of playback stalls.
- Total stall duration.
- Quality-of-experience (QoE) score.
- Response to changing network delay.
- Packet-loss recovery.
- The effect of FEC redundancy.
- Audio continuity during severe network degradation.

### Reported Simulation Results

The project's benchmark notes report the following results:

| Metric | Reported result |
|---|---:|
| Proposed controller: playback stalls | 0 |
| Proposed controller: stall duration | 0.00 s |
| BBA baseline: playback stalls | 6 |
| BBA baseline: stall duration | 16.70 s |
| Proposed approach: QoE score | 128.40 |
| Rate-based baseline: QoE score | 63.05 |

These figures represent the project's reported simulation results. Their interpretation depends on the benchmark configuration and test conditions.

A zero-stall result in a particular simulation does not guarantee zero stalls under every network condition. The accompanying benchmark metrics and comparison plot provide the relevant experimental context.

## 13. Limitations

- The simulator models network conditions and cannot reproduce every characteristic of a real network.
- XOR-based FEC can recover only losses supported by the available redundancy and recovery structure.
- FEC introduces overhead, which can affect performance when bandwidth is limited.
- Increasing delay can indicate congestion, but delay alone does not uniquely identify its cause.
- The custom RTP-like header does not imply complete compliance with the RTP standard.
- Benchmark results depend on the simulation settings, implementation, and baseline configurations.
- Wireshark and Mininet workflows depend on the local environment and installed tools.

The project is intended as an educational and experimental simulator rather than a production-ready streaming protocol.

## 14. Troubleshooting

| Problem | Suggested action |
|---|---|
| Python is not recognized | Check the Python installation or use `python3`. |
| A dependency is missing | Install the packages listed in `requirements.txt`. |
| Dashboard does not open | Confirm that `web_dashboard.py` is running and port `8080` is available. |
| Benchmark fails | Review the error output and relevant dependencies. |
| Tests fail | Review the test output and consult `docs/test_report.md`. |
| Capture file cannot be opened | Confirm that the `.pcap` file exists and is valid. |
| Lua dissector does not load | Check Wireshark's Lua support and the path to the script. |
| Mininet does not run | Check the Linux environment, installation, permissions, and topology requirements. |

## 15. References

1. **Python Documentation:** https://docs.python.org/3/
2. **RFC 3550 — RTP: A Transport Protocol for Real-Time Applications:** https://www.rfc-editor.org/rfc/rfc3550
3. **RFC 5109 — RTP Payload Format for Generic Forward Error Correction:** https://www.rfc-editor.org/rfc/rfc5109
4. **Wireshark Documentation:** https://www.wireshark.org/docs/
5. **Mininet Documentation:** http://mininet.org/
6. **Matplotlib Documentation:** https://matplotlib.org/stable/
7. **Python `struct` Documentation:** https://docs.python.org/3/library/struct.html

These references provide background on the technologies and networking concepts used in the project.

## 16. Computer Networks Course Relevance

| Course concept | Application in the project |
|---|---|
| UDP communication | Datagram-based streaming simulation |
| Protocol design | Custom RTP-like binary packet header |
| Congestion awareness | Delay-gradient analysis |
| Adaptive transmission | Network-aware streaming control |
| Error control | XOR-based Forward Error Correction |
| Packet loss | Simulated loss and recovery experiments |
| Network performance | Stall and QoE evaluation |
| Packet analysis | Wireshark and Lua dissector |
| Network emulation | Optional Mininet topology |
| Visualization | Benchmark comparison and web dashboard |

The project applies networking concepts through implementation, simulation, testing, and performance analysis. Python, Mininet, Wireshark, and visualization are represented in the documented workflows. The dashboard architecture uses Python's built-in `http.server`; Flask should only be listed as an implemented technology if it is actually used in the submitted code.

## 17. Conclusion

The Cross-Layer Delay-Gradient ABR Streaming Simulator explores a coordinated approach to adaptive streaming by combining delay-aware control, dynamic XOR-based error recovery, and audio-first graceful degradation.

Through protocol handling, network simulation, adaptive control, benchmarking, visualization, and packet analysis, the project provides a practical environment for studying the relationship between network conditions and streaming continuity.

The simulator supports experimentation with the trade-offs between video quality, packet-loss recovery, redundancy, and audio continuity under changing network conditions.

---

**Project:** Cross-Layer Delay-Gradient ABR Streaming Simulator with Dynamic XOR FEC & Audio-First Survival  
**Course:** Computer Networks  
**Institution:** MIT World Peace University, Pune  
**Evaluators:** Dr. Uma Pujeri and Dr. Swati
