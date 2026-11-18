#!/usr/bin/env python3
"""How often does a cluster-bootstrap percentile interval cover the truth
when there are as few clusters as in this analysis?

The intervals in this repository resample whole configurations. A rate that
concerns one method on one task rests on about eight configurations, each
with one to three runs. With so few clusters a percentile interval is known
to be too narrow. This script measures by how much, for clusters sized like
the ones behind the differential expression trap rate.

Each simulated configuration gets its own pass probability, drawn from a
beta distribution with mean 0.65. The spread of that distribution sets how
alike the repeats of one configuration are (the intraclass correlation).
Runs are then drawn, the interval is computed exactly as in
`sc_zprime.uncertainty`, and the script counts how often it contains 0.65.

Needs only numpy. Takes a few seconds.

    python scripts/interval_coverage.py
"""

import numpy as np

SIZES = [3, 3, 3, 3, 3, 3, 1, 1]  # trap-method runs per configuration on the differential expression task
EMPTY = 8                         # configurations with no trap-method run; they are resampled too
MEAN = 0.65
SIMULATIONS = 4000
RESAMPLES = 2000


def coverage(intraclass: float, rng: np.random.Generator, simulations: int = SIMULATIONS,
             resamples: int = RESAMPLES) -> float:
    total = 1.0 / intraclass - 1.0
    a, b = MEAN * total, (1.0 - MEAN) * total
    sizes = np.array(SIZES + [0] * EMPTY)
    hits = 0
    for _ in range(simulations):
        p = rng.beta(a, b, len(SIZES))
        passes = np.concatenate([rng.binomial(SIZES, p), np.zeros(EMPTY, int)])
        pick = rng.integers(0, len(sizes), size=(resamples, len(sizes)))
        den = sizes[pick].sum(axis=1)
        num = passes[pick].sum(axis=1)
        rate = num[den > 0] / den[den > 0]
        low, high = np.percentile(rate, [2.5, 97.5])
        hits += low <= MEAN <= high
    return hits / simulations


def main() -> None:
    rng = np.random.default_rng(20261118)
    print("nominal coverage: 95%")
    for intraclass in (0.1, 0.3, 0.5, 0.7):
        print(f"intraclass correlation {intraclass:.1f}: interval covers the truth in {coverage(intraclass, rng):.1%} of simulations")


if __name__ == "__main__":
    main()
