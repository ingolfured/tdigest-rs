# tdigest-rs

This candidate preserves the original `tdigest_rs` Python API and calculations,
and adds a separate modern engine through `gr_tdigest`. Existing applications
keep their imports, `delta` argument, array dtypes and original state behavior.
The modern API is an explicit choice; it does not silently replace those answers.

```python
import numpy as np
from tdigest_rs import TDigest as OriginalTDigest
from gr_tdigest import TDigest as ModernTDigest

values = np.array([1.0, 2.0, 3.0], dtype=np.float64)
original = OriginalTDigest.from_array(values, delta=300.0)
modern = ModernTDigest.from_array(values, max_size=1000, scale="k2")
```

Install the distribution as `tdigest-rs` for NumPy use, or `tdigest-rs[polars]`
for the modern Polars expressions. The declared runtime range is CPython
3.10–3.12 with NumPy `>=1.26.4,<3`. The optional Polars extra pins the tested
plugin version `1.34.0`. These are candidate support bounds, not a claim that
this branch's wheels have passed every platform gate.

Do not co-install this distribution with the private `gr-tdigest` distribution:
both own `tdigest_rs` and `gr_tdigest` files. The intended migration is an upgrade
of the existing `tdigest-rs` distribution. An environment containing the private
distribution needs an explicit package transition; install order is not a safe
ownership policy.

The original standalone Rust package is `tdigest_core` in `src/upstream`. It
preserves the original public fields and methods and the pinned calculations.
The modern root package is provisionally `tdigest-rs` version `2.0.0`, with Rust
library name `gr_tdigest`. A Rust consumer using the repository root as a path
dependency must select the nested original package explicitly. The provisional
root version is not a release or registry-ownership decision.

Read [the review guide](docs/review-refresh.md) for the compatibility boundary,
modern tradeoffs and remaining rollout gates. The modern API and numerical
contracts are in [api_design.md](api_design.md) and
[tdigest_design.md](tdigest_design.md). The unchanged original test-suite
provenance is in [compat/tdigest-rs-upstream](compat/tdigest-rs-upstream/PROVENANCE.md).

For local Linux development:

```sh
make setup
make build
make test
make python-support-test
```

The installed-wheel gate builds one release Linux wheel and checks it outside
the checkout on six Python/NumPy combinations plus a Polars-free baseline.
The upstream CI platform matrix remains configured separately; a local Linux
wheel is not a manylinux, musllinux, macOS or Windows validation result.

Publishing follows the existing upstream workflows and environments described
in [PUBLISH.md](PUBLISH.md). No package publication is part of this candidate.
