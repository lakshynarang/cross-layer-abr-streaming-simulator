"""
network_channel.py — Intermediate UDP Network Channel Emulator
==============================================================
Implements a realistic transport-layer network impairment proxy supporting both:
1. Live Raw UDP Socket Proxy Thread (`UDPNetworkChannelProxy`):
   - Listens on a local UDP ingress port, applies Token Bucket rate shaping, bottleneck FIFO
     queueing delay (`D_queue`), constant propagation delay + Gaussian jitter, and Uniform
     or Gilbert-Elliott 2-State Markov burst packet loss before forwarding to the egress port.
2. High-Speed Discrete-Event / Trace Channel Emulator (`VirtualNetworkChannel`):
   - Shares the exact same physics engine (Token Bucket + FIFO bottleneck queue + Gilbert-Elliott
     Markov chain + Gaussian jitter) for deterministic multi-algorithm benchmark evaluations.

Configurable Parameters (exposed to CLI & Web Sliders):
-------------------------------------------------------
- Bottleneck Bandwidth : 200 Kbps to 10,000 Kbps (10 Mbps) via Token Bucket + FIFO Queue
- Base Propagation RTT : Constant delay (e.g. 40ms - 100ms) + Gaussian jitter (e.g. ±15ms)
- Loss Engine          :
    * "uniform"        : Bernoulli i.i.d. random drop with probability `uniform_loss_prob`
    * "gilbert_elliott": 2-State Markov Chain (GOOD <-> BAD burst state)
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
import heapq
import math
import random
import socket
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ChannelConfig:
    """Configurable network impairment parameters (exposed to sliders and trace profiles)."""
    bandwidth_kbps: float = 4500.0        # Range: 200 Kbps .. 10,000 Kbps (10 Mbps)
    base_delay_ms: float = 50.0           # Constant one-way/RTT propagation delay (ms)
    jitter_std_ms: float = 15.0           # Gaussian jitter standard deviation (ms)
    loss_mode: str = "gilbert_elliott"    # "uniform" or "gilbert_elliott"
    uniform_loss_prob: float = 0.0        # 0.0 .. 0.50 (used when loss_mode == "uniform")
    # Gilbert-Elliott 2-State Markov parameters:
    ge_p_good_to_bad: float = 0.04        # Transition prob P(GOOD -> BAD)
    ge_r_bad_to_good: float = 0.25        # Transition prob P(BAD  -> GOOD)
    ge_loss_in_good: float = 0.002        # Drop prob in GOOD state (0.2%)
    ge_loss_in_bad: float = 0.45          # Drop prob in BAD burst state (45%)
    max_queue_ms: float = 250.0           # Bottleneck router FIFO buffer capacity (tail-drop threshold)


class GilbertElliottLossEngine:
    """
    Implements both Uniform Random Loss and the Gilbert-Elliott 2-State Markov Burst Loss model.
    In the Gilbert-Elliott model:
      State S_n in {GOOD (0), BAD (1)}
      Steady-state probability of BAD burst state: pi_B = p / (p + r)
      Average burst length: L_burst = 1 / r packets
    """

    STATE_GOOD = 0
    STATE_BAD = 1

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self.state: int = self.STATE_GOOD
        self.total_packets: int = 0
        self.dropped_packets: int = 0
        self.bad_state_packets: int = 0

    def reset(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self.state = self.STATE_GOOD
        self.total_packets = 0
        self.dropped_packets = 0
        self.bad_state_packets = 0

    def should_drop(self, config: ChannelConfig) -> Tuple[bool, str]:
        """
        Determines whether the current packet is dropped by the channel loss engine.
        Returns (dropped: bool, state_label: str).
        """
        self.total_packets += 1

        if config.loss_mode == "uniform":
            dropped = self.rng.random() < config.uniform_loss_prob
            if dropped:
                self.dropped_packets += 1
            return dropped, "UNIFORM"

        # Gilbert-Elliott 2-state Markov transition step
        u = self.rng.random()
        if self.state == self.STATE_GOOD:
            if u < config.ge_p_good_to_bad:
                self.state = self.STATE_BAD
        else:
            if u < config.ge_r_bad_to_good:
                self.state = self.STATE_GOOD

        if self.state == self.STATE_BAD:
            self.bad_state_packets += 1
            drop_prob = config.ge_loss_in_bad
            state_name = "GE_BAD_BURST"
        else:
            drop_prob = config.ge_loss_in_good
            state_name = "GE_GOOD"

        dropped = self.rng.random() < drop_prob
        if dropped:
            self.dropped_packets += 1
        return dropped, state_name

    @staticmethod
    def theoretical_average_loss(config: ChannelConfig) -> float:
        """Computes the exact steady-state expected packet loss rate."""
        if config.loss_mode == "uniform":
            return config.uniform_loss_prob
        denom = config.ge_p_good_to_bad + config.ge_r_bad_to_good
        if denom <= 0:
            return config.ge_loss_in_good
        pi_bad = config.ge_p_good_to_bad / denom
        pi_good = 1.0 - pi_bad
        return pi_good * config.ge_loss_in_good + pi_bad * config.ge_loss_in_bad


class TokenBucketBottleneck:
    """
    Models a physical bottleneck link with a Token Bucket rate shaper and a bounded FIFO queue.
    - Tokens replenish at `bandwidth_kbps * 1000 / 8` bytes per second.
    - When sending rate exceeds the token replenishment rate, excess bytes accumulate in the
      virtual FIFO bottleneck queue, directly generating physical queueing delay:
          D_queue (ms) = (queue_bytes * 8) / bandwidth_kbps
    - If `D_queue > max_queue_ms`, tail-drop congestion loss occurs!
    """

    def __init__(self, bucket_capacity_bytes: int = 12000) -> None:
        self.bucket_capacity_bytes = bucket_capacity_bytes
        self.tokens_bytes: float = float(bucket_capacity_bytes)
        self.queue_backlog_bytes: float = 0.0
        self.last_update_time_s: float = 0.0
        self.tail_drops: int = 0

    def reset(self, current_time_s: float = 0.0) -> None:
        self.tokens_bytes = float(self.bucket_capacity_bytes)
        self.queue_backlog_bytes = 0.0
        self.last_update_time_s = current_time_s
        self.tail_drops = 0

    def process_packet(
        self, packet_bytes: int, current_time_s: float, config: ChannelConfig
    ) -> Tuple[bool, float]:
        """
        Passes a packet of size `packet_bytes` through the Token Bucket + Bottleneck FIFO Queue.
        Returns:
          (tail_dropped: bool, queueing_delay_ms: float)
        """
        dt = max(0.0, current_time_s - self.last_update_time_s)
        self.last_update_time_s = current_time_s

        rate_bytes_per_sec = max(25_000.0, (config.bandwidth_kbps * 1000.0) / 8.0)

        # Replenish tokens and service both existing backlog and arriving bytes over `dt`
        generated_bytes = dt * rate_bytes_per_sec
        used_tokens = min(self.tokens_bytes, float(packet_bytes))
        self.tokens_bytes -= used_tokens
        unburst_bytes = float(packet_bytes) - used_tokens
        total_to_service = self.queue_backlog_bytes + unburst_bytes

        if total_to_service <= generated_bytes:
            self.queue_backlog_bytes = 0.0
            leftover = generated_bytes - total_to_service
            self.tokens_bytes = min(float(self.bucket_capacity_bytes), self.tokens_bytes + leftover)
        else:
            self.queue_backlog_bytes = total_to_service - generated_bytes

        queueing_delay_ms = (self.queue_backlog_bytes / rate_bytes_per_sec) * 1000.0

        # Check router FIFO tail-drop limit (bufferbloat overflow)
        if queueing_delay_ms > config.max_queue_ms:
            self.queue_backlog_bytes = max(0.0, self.queue_backlog_bytes - packet_bytes)
            self.tail_drops += 1
            return True, config.max_queue_ms

        return False, queueing_delay_ms


class UDPNetworkChannelProxy:
    """
    Runs as an intermediate UDP proxy thread between Server and Client sockets.
    - Receives raw UDP packets on `listen_port`
    - Applies Token Bucket bandwidth shaping, FIFO queueing delay, Constant Delay + Gaussian Jitter,
      and Uniform / Gilbert-Elliott Markov burst loss
    - Forwards surviving packets to `(target_host, target_port)` at their scheduled release timestamp.
    """

    def __init__(
        self,
        listen_port: int,
        target_port: int,
        config: Optional[ChannelConfig] = None,
        seed: int = 42,
    ) -> None:
        self.listen_port = listen_port
        self.target_port = target_port
        self.config = config or ChannelConfig()
        self.loss_engine = GilbertElliottLossEngine(seed=seed)
        self.shaper = TokenBucketBottleneck()
        self.rng = random.Random(seed + 100)

        self._lock = threading.Lock()
        self._running = False
        self._rx_thread: Optional[threading.Thread] = None
        self._tx_thread: Optional[threading.Thread] = None
        self._delay_heap: List[Tuple[float, int, bytes]] = []
        self._pkt_counter = 0
        self._cv = threading.Condition()

        self.sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_in.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock_in.bind(("127.0.0.1", self.listen_port))
        self.sock_in.settimeout(0.05)

        self.sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Telemetry counters
        self.stats = {
            "total_ingress_packets": 0,
            "forwarded_packets": 0,
            "channel_loss_drops": 0,
            "congestion_tail_drops": 0,
            "last_queue_delay_ms": 0.0,
            "last_total_rtt_ms": self.config.base_delay_ms,
            "ge_state": "GE_GOOD",
        }

    def update_config(self, new_config: ChannelConfig) -> None:
        with self._lock:
            self.config = new_config

    def start(self) -> None:
        self._running = True
        self.shaper.reset(time.monotonic())
        self._rx_thread = threading.Thread(target=self._ingress_loop, daemon=True)
        self._tx_thread = threading.Thread(target=self._egress_loop, daemon=True)
        self._rx_thread.start()
        self._tx_thread.start()

    def stop(self) -> None:
        self._running = False
        with self._cv:
            self._cv.notify_all()
        if self._rx_thread and self._rx_thread.is_alive():
            self._rx_thread.join(timeout=0.5)
        if self._tx_thread and self._tx_thread.is_alive():
            self._tx_thread.join(timeout=0.5)
        self.sock_in.close()
        self.sock_out.close()

    def _ingress_loop(self) -> None:
        while self._running:
            try:
                raw_data, _ = self.sock_in.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break

            now = time.monotonic()
            with self._lock:
                cfg = self.config
                self.stats["total_ingress_packets"] += 1

                # 1. Token Bucket + Bottleneck FIFO Queue
                tail_dropped, q_delay_ms = self.shaper.process_packet(len(raw_data), now, cfg)
                self.stats["last_queue_delay_ms"] = q_delay_ms
                if tail_dropped:
                    self.stats["congestion_tail_drops"] += 1
                    continue

                # 2. Channel Loss Engine (Uniform or Gilbert-Elliott 2-State Markov)
                channel_dropped, state_label = self.loss_engine.should_drop(cfg)
                self.stats["ge_state"] = state_label
                if channel_dropped:
                    self.stats["channel_loss_drops"] += 1
                    continue

                # 3. Propagation Delay + Gaussian Jitter
                jitter_ms = self.rng.gauss(0.0, cfg.jitter_std_ms)
                prop_delay_ms = max(2.0, cfg.base_delay_ms + jitter_ms)
                total_delay_ms = prop_delay_ms + q_delay_ms
                self.stats["last_total_rtt_ms"] = total_delay_ms

                release_time = now + (total_delay_ms / 1000.0)
                self._pkt_counter += 1
                item = (release_time, self._pkt_counter, raw_data)

            with self._cv:
                heapq.heappush(self._delay_heap, item)
                self._cv.notify()

    def _egress_loop(self) -> None:
        while self._running:
            with self._cv:
                while self._running and not self._delay_heap:
                    self._cv.wait(timeout=0.05)
                if not self._running:
                    break
                release_time, _, payload = self._delay_heap[0]
                now = time.monotonic()
                wait_s = release_time - now
                if wait_s > 0:
                    self._cv.wait(timeout=min(wait_s, 0.02))
                    continue
                heapq.heappop(self._delay_heap)

            try:
                self.sock_out.sendto(payload, ("127.0.0.1", self.target_port))
                with self._lock:
                    self.stats["forwarded_packets"] += 1
            except OSError:
                break
