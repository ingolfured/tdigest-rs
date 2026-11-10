# Python and NumPy API

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

## Capacity-based digests

The remaining sections describe digests constructed with `max_size=`.

```python
from tdigest_rs import TDigest
d = TDigest.from_array([0.0, 10.0], weights=[9.0, 1.0], max_size=1000)
assert d.median() == d.quantile(0.5) == 0.0
```

Use the named constructors; `TDigest()` is not a constructor. `from_array(data,
*, max_size, scale=..., singleton_policy=..., pin_per_side=None,
weights=..., precision="auto", f32_mode=None)` copies scalar or one-dimensional
training data. `arr=` remains a supported spelling for `data`. Unknown arguments
raise `TypeError`. Invalid values, lengths, configuration or representability
raise `ValueError`.

With `max_size=`, the defaults are K2, singleton Use and Float64 means. Object
`precision="auto"` selects Float64, even for Float32 input. Explicit `f32` stores
Float32 means/extrema; all weights, `count` and `sum` remain Float64. Capacity is
a compression/storage setting, not observation count. The Python convenience
constructor accepts capacities 10–20,000. Explicit 200 and 1,000 remain supported.
The lower-level Rust builder supports smaller capacities, covered separately.

Use the `scale`, `singleton_policy` and `pin_per_side` settings with capacity-based construction.

`from_means_weights(means, weights, ...)` constructs **weighted observations**.
It cannot restore compressed extrema, original sums or point/mixed identity.
For a full-state copy use `copy.copy`, `copy.deepcopy`, pickle or TDIG bytes.

## Queries and containers

`cdf(x)`, `quantile(q)`, `median()` and `trimmed_mean(lower, upper)` do not mutate
the digest. `median()` is `quantile(0.5)`. CDF at a tied value is the mass below
plus half the mass at that value, divided by total mass. Quantile endpoints are
the observed extrema.

| Probe input | Modern result |
|---|---|
| Python scalar or zero-dimensional NumPy array | Python float |
| list | list of floats |
| tuple | tuple of floats |
| one-dimensional NumPy array, including one element | Independent writable Float64 array, same length |
| multidimensional input | Explicit error; flatten and reshape in the application |

This is a documented migration from historical modern floating shape/dtype
preservation. Integer NumPy probes always produce floating probabilities.

Quantile probabilities must be finite and in `[0,1]`, including rejection of
NaN. CDF of NaN is NaN. For nonempty state, CDF at negative/positive infinity is
zero/one. Empty queries return NaN.

## Updates, ownership and transforms

`add(values)`, `add_weighted(values, weights)`, `merge(other_or_iterable)`,
`scale_weights(factor)` and `scale_values(factor)` mutate and return the receiver.
A failed modern update leaves it unchanged, including a later invalid item in a
merge iterable. Merges reject missing entries, mixed precision and differing
configuration, including empty inputs. Inputs to merge are not modified.
`TDigest.merge_all(inputs)` returns independent state; an empty iterable returns
Float64/1000/K2/Use empty state. It does not filter `None`.

Weights and scale factors must be finite and strictly positive. Fractional mass
is supported. Reweighting changes weights/count/sum and preserves the value
axis. Value scaling changes means/extrema/sum and preserves mass. Transform a
copy without modifying the source:

```python
import copy
scaled = copy.copy(d).scale_values(2.0)
assert d.max == 10.0 and scaled.max == 20.0
```

`cast_precision("f32" | "f64")` returns independent state, retaining Float64
mass. Conversion that overflows, underflows to zero or produces invalid ordering
is rejected. Scale operations likewise reject unrepresentable products. Finite
individual inputs do not guarantee a representable aggregate: overflowing mass
or weighted sum is rejected. A nonzero weighted product rounding to zero is also
rejected. No promise is made that every increment is distinguishable beside an
arbitrarily large Float64 total. See the [accuracy tests](../../tests/quality/README.md) for measured limits.

`means` and `weights` return independent Float64 arrays. `count` means total mass;
`len(d)` means centroid count. `sum`, `min`, `max`, `max_size`, `scale`, `delta`
describe the stored state. Empty state has zero count/sum, no centroids and NaN
extrema. Input buffers are never retained. Independent digests can be used from
independent threads; concurrent mutation of one digest is not supported.

## Saved state and installed documentation

`to_bytes(version=3)` is the full-state format; `from_bytes` validates and owns
the restored state. V1/v2 reads remain supported with documented historical
inference. Older writes reject unsupported fractional mass or configuration.
V3 extensions are not automatically readable by every older v3 reader.

`to_dict()` contains a readable snapshot plus `wire_b64_v3`. Binary state is
authoritative when present: editing readable fields does not change restored
state. A dictionary with only means/weights constructs observations, not a
lossless restoration. For delta-mode dictionaries and pickles, see the [migration guide](../../ROLLOUT.md).

The wheel ships `py.typed` and class/expression stubs. `help(TDigest)` and native
method docstrings describe the actual installed class. For Polars expressions,
use the separate [Polars guide](POLARS_API.md) and install `tdigest-rs[polars]`.
