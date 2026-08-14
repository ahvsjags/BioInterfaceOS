"""Verify the frozen T277 T250 replicate-aware refit."""

from pathlib import Path

from biointerfaceos.r4_t277_t250_replicate_aware_refit import (
    R4T277T250ReplicateAwareRefitWorkflow,
)

if __name__ == "__main__":
    summary = R4T277T250ReplicateAwareRefitWorkflow(Path.cwd()).verify(strict=True)
    print(summary)
