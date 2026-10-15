# tdigest-rs for Python

`tdigest_rs.TDigest` keeps the original Python API and numerical implementation.
The modern engine is available separately as `gr_tdigest.TDigest`.

Install `tdigest-rs` for NumPy use, or `tdigest-rs[polars]` for modern Polars
expressions. The candidate runtime contract is CPython 3.10–3.12 with NumPy
`>=1.26.4,<3`; the optional Polars extra pins version `1.34.0`.

```python
import numpy as np
from tdigest_rs import TDigest

digest = TDigest.from_array(np.array([1.0, 2.0, 3.0]), delta=300.0)
print(digest.median())
```

Do not co-install the private `gr-tdigest` distribution: it owns overlapping
Python package paths. See the repository README and `docs/review-refresh.md`
for upgrade, saved-state, Rust API and platform limitations.
