# Cross-Layer Delay-Gradient ABR Streaming Simulator with Dynamic XOR FEC & Audio-First Survival

**Course:** Computer Networks  
**Institution:** MIT World Peace University, Pune  
**Project Type:** Computer Networks Mini Project  
**Evaluators:** Dr. Uma Pujeri and Dr. Swati

---

## 1. Project Overview

This project implements a Python-based adaptive audio/video streaming simulator designed to study streaming performance under unstable network conditions. It combines delay-gradient-based congestion awareness, adaptive bitrate (ABR) control, dynamic XOR-based Forward Error Correction (FEC), and audio-first graceful degradation.

Conventional adaptive streaming approaches often depend on throughput estimates or buffer occupancy to decide when to adjust video quality. These approaches may not always respond quickly to sudden changes in network conditions.

Our simulator explores a cross-layer approach in which changes in network delay help guide adaptation decisions, XOR-based redundancy supports packet-loss recovery, and audio is prioritized when network conditions become severe.

The project integrates protocol design, UDP communication, network simulation, adaptive streaming control, error recovery, testing, benchmarking, visualization, and packet analysis into a single experimental framework.

## 2. Project Objectives

- Implement UDP-based streaming communication using a custom RTP-like binary packet header.
- Monitor changes in network delay and use delay gradients to help identify congestion.
- Adapt streaming decisions according to simulated network conditions.
- Implement XOR-based Forward Error Correction for recovering eligible packet losses.
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

The simulator explores reducing or suspending video delivery while prioritizing audio and applying additional protection where supported by the implementation.

## 4. System Architecture

The project is divided into components that handle packet representation, adaptive control, error recovery, network behaviour, streaming execution, and performance evaluation.

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

The diagram represents the high-level design. The precise execution sequence is determined by the implementation in the source files.

### Packet Format

The project uses a custom 16-byte RTP-like binary header encoded using Python's `struct` module and network byte order.

The documented format string is:

```python
struct.pack('!HIBBBBHI', ...)
```

The `!` indicates network byte order (big-endian). This is a project-specific RTP-like format and should not be interpreted as full compliance with the standard RTP protocol.

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

The documented dashboard architecture uses Python's built-in `http.server`. Flask should only be considered a project dependency if the submitted implementation actually imports or uses it.

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

### Main Files

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
| `mininet_topology.py` | Optional Mininet experiments |
| `wireshark_capture.py` | Packet-capture workflow support |
| `wireshark_dissector.lua` | Custom Wireshark dissector |
| `benchmark_comparison.png` | Benchmark comparison visualization |
| `benchmark_metrics.json` | Structured benchmark metrics |
| `stream_capture.pcap` | Packet-capture artifact |
| `docs/architecture.md` | Architecture documentation |
| `docs/test_report.md` | Test report documentation |
| `requirements.txt` | Python dependencies |

The root-level result files and the files in `output/` are listed separately because both locations are present in the repository. Check the latest generated output before assuming that the copies are identical.

## 7. Prerequisites

For the core simulator, install:

- Python 3.10 or newer.
- pip, Python's package installer.
- Git, if cloning the repository.
- A modern web browser for the dashboard.

Additional tools are required only for optional workflows:

- **Wireshark:** for inspecting packet captures.
- **Mininet:** for network-topology experiments on a supported Linux environment.

## 8. Steps to Run the Project

Follow these steps from the repository's root directory.

### Step 1: Download the Project

Clone the GitHub repository:

```bash
git clone https://github.com/YOUR-USERNAME/cross-layer-abr-streaming-simulator.git
cd cross-layer-abr-streaming-simulator
```

Replace `YOUR-USERNAME` with your GitHub username and confirm that the repository name matches your actual repository.

Alternatively, download the repository as a ZIP file from GitHub, extract it, and open a terminal in the extracted project folder.

### Step 2: Install Dependencies

Install the dependencies listed in `requirements.txt`:

```bash
python -m pip install -r requirements.txt
```

If your system uses `python3`, run:

```bash
python3 -m pip install -r requirements.txt
```

If the installation fails, check that Python and pip are installed and that the packages in `requirements.txt` are compatible with your Python version.

### Step 3: Run the Benchmark

Execute:

```bash
python benchmark.py
```

This runs the project's benchmark workflow.

Review the terminal output and the generated result files. The repository contains benchmark artifacts named:

- `benchmark_metrics.json`
- `benchmark_comparison.png`

The `output/` folder also contains copies of these artifacts. Check the paths printed by the script or inspect the relevant source code to confirm where the latest results are written.

The JSON file contains structured metrics, while the PNG file provides a visual comparison of benchmark results.

### Step 4: Launch the Web Dashboard

Start the dashboard server:

```bash
python web_dashboard.py
```

Once the server starts, open the following address in your browser:

**http://127.0.0.1:8080**

Keep the terminal open while using the dashboard. Stop the server with `Ctrl+C` when finished.

If the page does not load, confirm that the server started successfully and that port `8080` is available.

### Step 5: Run the Tests

Execute the test script:

```bash
python test_simulator.py -v
```

The `-v` option requests verbose output if supported by the script.

If the script does not accept this option, run:

```bash
python test_simulator.py
```

Review the test results and investigate any failures before drawing conclusions about the simulator's correctness.

For the documented testing procedure and results, see [`docs/test_report.md`](docs/test_report.md).

### Step 6: Inspect the Architecture

To understand the system's design and component interactions, open:

[`docs/architecture.md`](docs/architecture.md)

This document provides additional architecture information beyond the overview in this README.

### Step 7: Inspect the Benchmark Results

Open `benchmark_comparison.png` to view the benchmark visualization and `benchmark_metrics.json` to inspect the recorded metrics.

The corresponding files in `output/` can also be inspected.

Use the results produced by the latest benchmark run when preparing demonstrations or reports. Previously generated files may reflect different settings or earlier runs.

## 9. Wireshark Packet Analysis

The repository includes a packet capture and a Lua dissector for inspecting the project's custom packet format.

### Step 1: Locate the Capture File

The repository contains a capture named:

```text
stream_capture.pcap
```

A copy is also listed in:

```text
output/stream_capture.pcap
```

If the capture file is present and valid, you can open it directly in Wireshark.

### Step 2: Open the Capture

If Wireshark is installed, open the capture from the terminal:

```bash
wireshark output/stream_capture.pcap
```

Alternatively, launch Wireshark and select **File → Open**, then choose the capture file.

### Step 3: Load the Custom Lua Dissector

The project includes:

```text
wireshark_dissector.lua
```

On a system where Wireshark supports Lua dissectors, you can try loading the script when opening the capture:

```bash
wireshark -X lua_script:wireshark_dissector.lua output/stream_capture.pcap
```

This command assumes the executable is named `wireshark`, the Lua script is in the current directory, and the capture is at the specified path.

The dissector must match the actual packet format to decode fields correctly. If Wireshark does not load the script or display the expected fields, consult its Lua configuration and the implementation of the dissector.

### What to Observe

- Packet arrival timing.
- Packet sequence and header information, where available.
- Traffic behaviour under simulated network impairments.
- FEC-related packets and recovery behaviour, if represented in the capture.
- Any changes in packet transmission during adaptation.

A packet capture alone does not establish that every lost packet was recovered or that playback remained uninterrupted. Compare observations with the benchmark output and test report.

### Optional: Run the Capture Script

The repository also contains:

```text
wireshark_capture.py
```

Its exact arguments and execution behaviour depend on its implementation. Inspect the script before running it to determine whether it creates a capture, invokes Wireshark, or requires additional parameters.

## 10. Optional Mininet Experiments

The repository includes `mininet_topology.py` for optional topology-based network experiments.

Mininet generally requires a supported Linux environment and appropriate permissions. It is not required for the basic Python benchmark or dashboard workflow.

On a configured Linux system, the following is the expected form of command if the script is designed to launch its topology directly:

```bash
sudo python3 mininet_topology.py
```

Before running it, inspect the script to confirm its requirements and behaviour. Use the instructions defined by the implementation if additional arguments, setup steps, or configuration are required.

If Mininet is unavailable, the core simulator can still be explored independently of this optional workflow.

## 11. Performance Evaluation

The project evaluates streaming behaviour under simulated network conditions and compares the proposed approach with available baseline strategies.

Relevant performance measures may include:

- Number of playback stalls.
- Total stall duration.
- Quality-of-experience (QoE) score.
- Response to changing network delay.
- Packet-loss recovery.
- The effect of FEC redundancy.
- Audio continuity during severe degradation.

The actual metrics depend on the benchmark implementation.

### Previously Reported Simulation Results

The project's earlier benchmark notes reported the following results:

| Metric | Reported result |
|---|---:|
| Proposed controller: playback stalls | 0 |
| Proposed controller: stall duration | 0.00 s |
| BBA baseline: playback stalls | 6 |
| BBA baseline: stall duration | 16.70 s |
| Proposed approach: QoE score | 128.40 |
| Rate-based baseline: QoE score | 63.05 |

These are reported project results and have not been independently verified in this README. Confirm them against the current `benchmark_metrics.json` and a fresh benchmark run before presenting them as final results.

Results from a simulation depend on its configuration and test conditions; they are not guarantees of performance on every real network.

## 12. Limitations

- The simulator models network conditions and cannot reproduce every characteristic of a real network.
- XOR-based FEC can recover only losses supported by the available redundancy and recovery structure.
- FEC adds overhead, which can affect performance when bandwidth is limited.
- Increasing delay can indicate congestion, but delay alone does not uniquely identify its cause.
- The custom RTP-like header is not a claim of complete RTP standards compliance.
- Benchmark results may change with network settings, implementation details, and baseline configurations.
- Wireshark and Mininet workflows depend on local tool installations and operating-system support.

The project is intended as an educational and experimental simulator, not a production-ready streaming protocol.

## 13. Troubleshooting

| Problem | Suggested action |
|---|---|
| Python is not recognized | Install Python or use the appropriate executable, such as `python3`. |
| A dependency is missing | Install the dependencies listed in `requirements.txt`. |
| Dashboard does not open | Confirm that `web_dashboard.py` is running and port `8080` is available. |
| Benchmark fails | Read the error output and check the relevant source code and dependencies. |
| Tests fail | Review the failed test output and consult `docs/test_report.md`. |
| Capture file cannot be opened | Verify that the `.pcap` file exists and is a valid capture. |
| Lua dissector does not load | Check Wireshark's Lua support and the path to the script. |
| Mininet does not run | Verify the Linux environment, Mininet installation, permissions, and topology requirements. |

## 14. References

1. **Python Documentation** — https://docs.python.org/3/
2. **RFC 3550: RTP — A Transport Protocol for Real-Time Applications** — https://www.rfc-editor.org/rfc/rfc3550
3. **RFC 5109: RTP Payload Format for Generic Forward Error Correction** — https://www.rfc-editor.org/rfc/rfc5109
4. **Wireshark Documentation** — https://www.wireshark.org/docs/
5. **Mininet Documentation** — http://mininet.org/
6. **Matplotlib Documentation** — https://matplotlib.org/stable/
7. **Python `struct` Documentation** — https://docs.python.org/3/library/struct.html

These references provide background on the underlying technologies. They do not independently validate the project's implementation or experimental results.

## 15. Computer Networks Course Relevance

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
| Visualization | Benchmark comparison and dashboard |

The course checklist mentions Python, Mininet, Wireshark, Flask, and visualization. Python, Mininet, Wireshark, and visualization are represented in the documented project workflows. The documented dashboard architecture uses Python's built-in `http.server`; Flask should only be claimed as used if it is actually present in the submitted implementation.

## 16. Conclusion

The Cross-Layer Delay-Gradient ABR Streaming Simulator explores a coordinated approach to adaptive streaming by combining delay-aware control, dynamic XOR-based error recovery, and audio-first graceful degradation.

Through protocol handling, network simulation, adaptive control, benchmarking, visualization, and optional packet analysis, the project provides a practical environment for studying the relationship between network conditions and streaming continuity.

The simulator can be used to examine the trade-offs between video quality, packet-loss recovery, redundancy, and audio continuity under changing network conditions.

---

**Project:** Cross-Layer Delay-Gradient ABR Streaming Simulator with Dynamic XOR FEC & Audio-First Survival  
**Course:** Computer Networks  
**Institution:** MIT World Peace University, Pune  
**Evaluators:** Dr. Uma Pujeri and Dr. Swati
