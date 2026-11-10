# Upgrading from 0.1.0

Keep `from tdigest_rs import TDigest` and your existing `delta=` calls.
Omitting the sizing argument still selects `delta=300`. All **91 original
Python tests pass unchanged**, including after upgrading an environment from
the published 0.1.0 wheel. Both constructor modes now share a Rust engine.
Its interpolation and compression can change an approximate result.

## Existing code that gives the same answers

This example runs on both wheels and gives the same results for each assertion.
`merge` and `update` still return a new digest in the original Python API.

```python
import numpy as np
from tdigest_rs import TDigest

first = TDigest.from_array(np.array([10, 20, 30], dtype=np.float32), delta=300)
second = TDigest.from_array(np.array([40, 50], dtype=np.float32), delta=300)
combined = first.merge(second)

assert first.weights.sum() == 3
assert combined.weights.sum() == 5
assert combined.median() == 30
assert combined.quantile(0.95) == 50
assert combined.trimmed_mean(0.1, 0.9) == 30
restored = TDigest.from_dict(combined.to_dict())
assert restored.weights.sum() == 5
```

## Where a numerical result changes

| Same Python call on both wheels | Published 0.1.0 | 1.0 |
| --- | ---: | ---: |
| 10th percentile of `[1.0, 2.0]` | ≈0.7 | 1.0 |
| Median of `[0.0, 10.0]` with integer weights `[90, 10]` | 1.0 | 0.0 |

In the first case the old interpolation went below the smallest observation.
In the second, 90% of the mass is at zero. The new median returns that value.
If a downstream test compares exact estimates or a decision depends on crossing
a threshold, check it on representative data before upgrading.
[Accuracy by dataset and merge order](docs/upstream-1.0.0/comparison.md)

**Saved Python digests.** The upgrade and reinstall checks loaded 32 pickle
states created with the published wheel. Those pickles store centroid means
and weights. Version 1.0 reconstructs the digest from them and uses the new
interpolation when queried. [Upgrade and reinstall test](scripts/test_package_upgrade.py)

## Seven cases from the original test suite

Each row shows what happens if you switch the same Python input to
`max_size=`. Keeping `delta=` or omitting the sizing argument preserves the
original behavior in all seven cases. [Original test cases](tests/upstream_legacy/bindings/python/tests/test_tdigest.py)

| Input or operation | Existing calls (`delta=` or default) | With `max_size=` |
| --- | --- | --- |
| Three NaNs | Skips all three and returns an empty digest. | Rejects NaN during construction. |
| `[10, 20, NaN]` | Keeps 10 and 20. | Rejects the array because it contains a NaN. |
| `[-∞, +∞, +∞]` | Stores two endpoints, with weight two at +∞. | Rejects infinite training values. |
| `[-∞, -20, 8, 10, +∞]` | Keeps all five means, including the endpoints. | Rejects the array because it contains infinities. |
| Merge `[-∞, 1, 2, +∞, +∞]` with `[-∞, -∞, -1, 30, +∞, +∞]` | Combines repeated endpoints and returns six centroids. | Construction rejects each input before the merge. |
| A Float16 NumPy array | Raises `TypeError`. The original API accepts Float32 and Float64 arrays. | Accepts Float16 input. Default mean storage is Float64. |
| Merge digests built from Float32 and Float64 arrays | The arrays select different stored precisions, so a direct merge raises `TypeError`. | Both constructors default to Float64, so the merge succeeds with Float64 means. If you choose different stored precisions, cast explicitly before merging. |

To request a Float32 result in 1.0, use `left.cast_precision("f32").merge(right.cast_precision("f32"))`
on digests with compatible compression settings and values representable in Float32.

**Rust callers.** The standalone `tdigest_core` crate was removed. Consumers of
that crate must migrate to the root `tdigest-rs` crate and handle the checked
results of construction and merging. [Rust API](api_design.md)
