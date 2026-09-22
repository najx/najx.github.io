"""Counting what the two model APIs are asked, so the run log can say what it cost.

Neither Jev nor Claude is metered anywhere else: the workflow log printed
the Claude draft to the cent and said nothing about Jev, and the docs called
the Jev half "a few cents" without a measurement behind it. Every call site
now adds its response's usage here, and the CLI prints one line per model at
the end of a run.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class Meter:
    """Requests and tokens for one model, priced at list rates per million."""

    name: str
    usd_per_mtok_in: float
    usd_per_mtok_out: float = 0.0
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, input_tokens: int | None, output_tokens: int | None = 0) -> None:
        with self._lock:
            self.requests += 1
            self.input_tokens += int(input_tokens or 0)
            self.output_tokens += int(output_tokens or 0)

    def reset(self) -> None:
        with self._lock:
            self.requests = self.input_tokens = self.output_tokens = 0

    @property
    def cost_usd(self) -> float:
        return (self.input_tokens / 1e6 * self.usd_per_mtok_in
                + self.output_tokens / 1e6 * self.usd_per_mtok_out)

    def summary(self) -> str:
        """One log line: `Jev: 912 requests, 3,812,004 tokens in, $0.160`."""
        out = f", {self.output_tokens:,} out" if self.usd_per_mtok_out else ""
        return (f"{self.name}: {self.requests:,} requests, "
                f"{self.input_tokens:,} tokens in{out}, ${self.cost_usd:.3f}")
