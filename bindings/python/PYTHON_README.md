# tdigest-rs

Install `tdigest-rs` for the NumPy APIs or `tdigest-rs[polars]` for Polars
expressions.

Import `TDigest` from `tdigest_rs` for both modes. The original calling convention
uses `delta=` (default 300). It accepts Float32 and Float64 NumPy arrays, ignores
NaNs, retains infinite endpoints and returns a new digest from merge and update.
Pass `max_size=` for capacity-based compression, strict finite inputs, fractional
weights, CDF, in-place updates and TDIG serialization. Supply one sizing parameter
per constructor. Both modes use the same Rust core for finite data.

Compression, interpolation and restored-pickle queries use modern numerical
results. For example, the 10th percentile of `[1.0, 2.0]` changes from 0.7 to
1.0, and the median of `[0, 10]` with weights `[90, 10]` changes from 1 to 0.
Published 0.1.0 pickles carry centroid means and weights. Loading one reconstructs
a digest from those observations.

The package supports standard CPython 3.10–3.15. Python 3.10–3.12 supports
NumPy 1.26.4 or 2.x, Python 3.13–3.14 requires NumPy 2.3.4 or later in the
2.x line, and Python 3.15 requires NumPy 2.5.4 or later in that line. The
Polars extra accepts compatible installed versions from 1.0.0 onward.

See the [project README](https://github.com/G-Research/tdigest-rs) for build
instructions, release notes and language guides.
