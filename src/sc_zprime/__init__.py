"""sc-zprime: Z-prime for single-cell agent evals.

Assay validation for the benchmarks that grade AI agents on biology. A
benchmark task is treated as an assay: its readout is only worth trusting once
its controls are shown to separate, its repeats agree, and its pass window is
known not to sit on top of a cluster of answers.
"""

__version__ = "0.2.0"
