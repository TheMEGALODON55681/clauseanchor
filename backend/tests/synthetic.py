"""A made-up catalogue for tests. Every id, name and status here is invented and none is real.

The real 46 ids are Tanishq's. The ids below must never be copied from anywhere.
"""

from __future__ import annotations


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
