# Python compatibility

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

Run `make compat-test` for all 91 original tests. The [archived fixtures](numerical-parity/README.md) record historical outputs.
