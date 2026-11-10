# tdigest-rs

Install `tdigest-rs` for the NumPy APIs or `tdigest-rs[polars]` for Polars
expressions. Existing callers import `TDigest` from `tdigest_rs`. Import it
from `gr_tdigest` to use the modern engine with fractional weights and CDF.

The package supports standard CPython 3.10–3.15. Python 3.10–3.12 supports
NumPy 1.26.4 or 2.x, Python 3.13–3.14 requires NumPy 2.3.4 or later in the
2.x line, and Python 3.15 requires NumPy 2.5.4 or later in that line. The
Polars extra accepts compatible installed versions from 1.0.0 onward.

See the [project README](https://github.com/G-Research/tdigest-rs) for build
instructions, release notes and language guides.
