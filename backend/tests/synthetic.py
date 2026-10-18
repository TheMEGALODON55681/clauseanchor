"""Made-up test data: a catalogue and a clock that only moves when a test moves it.

Every catalogue id, name and status here is invented and none is real. The real 46 ids are
Tanishq's, and the ids below must never be copied from anywhere.
"""

from __future__ import annotations


class FakeClock:
    """The injected clock (one callable). Tests move time with `advance`, so nothing sleeps."""

    def __init__(self, now: float = 1_800_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def synthetic_catalogue() -> dict:
    return {
        "catalogue_version": "synthetic-test-0",
        "categories": [
            {
                "id": "synthetic.alpha",
                "display_name": "Synthetic Alpha",
                "source": "cuad",
                "support_status": "synthetic_status_a",
            },
            {
                "id": "synthetic.beta",
                "display_name": "Synthetic Beta",
                "source": "india_extension",
                "support_status": "synthetic_status_b",
            },
            {
                "id": "synthetic.gamma",
                "display_name": "Synthetic Gamma",
                "source": "cuad",
                "support_status": "synthetic_status_a",
            },
        ],
    }
