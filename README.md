# tdigest-rs

A t-digest summarizes observations for approximate percentile queries and can
merge summaries from separate batches. The proposed 1.0.0 release keeps the
original G-Research engine and adds a modern engine with CDF queries, fractional
weights and portable TDIG state. Start with the [maintainer review guide](REVIEW_GUIDE.md)
for the before/after comparison, speed measurements and test evidence.

## Choose a Python API

Existing applications use the original engine, including its uint32 weights,
immutable merge/update and historical pickle behavior.

```python
import numpy as np
from tdigest_rs import TDigest

original = TDigest.from_array(np.array([0., 1., 2., 3.]), delta=300)
print(original.median())
```

New applications can opt into the modern engine. Its capacity, scale and use
of atomic centroids affect numerical answers and storage.

```python
from gr_tdigest import TDigest

modern = TDigest.from_array([0., 1., 2., 3.], max_size=1000)
print(modern.quantile(0.5), modern.cdf(1.5))
```

The distribution name is `tdigest-rs`. Install `tdigest-rs[polars]` for Polars
expressions. Supported runtimes are standard CPython 3.10–3.15. For array
shapes, weight types, merge behavior and serialization, see the
[Python API](bindings/python/OBJECT_API.md) and [Polars API](bindings/python/POLARS_API.md).
The [rollout policy](ROLLOUT.md) describes continued legacy support, later
deprecation and eventual removal in a future major release.

## Rust, CLI and Java

The modern Rust crate exposes checked construction and merge operations.
The original `tdigest_core` crate lives in `src/upstream` and retains its
public means and uint32 weights. See its [provenance](src/upstream/PROVENANCE.md).

The Rust CLI can build a digest from a CSV column and query the saved file.

```sh
cargo run --release --bin tdigest -- build --input numbers.csv --input-format csv --input-column value --to-digest model.tdig
cargo run --release --bin tdigest -- quantile --from-digest model.tdig --p 0.5,0.99 --no-header
```

The Java API uses `com.gresearch.tdigest` and targets Java 11 bytecode.
See [JDK selection, native loading and offline builds](bindings/java/README.md)
and the [Scala, Kotlin and Spark examples](bindings/java/examples/README.md).

## Build and test

Use Rust 1.95.0, Python 3.12 for development and a supported JDK.

```sh
make setup
make build
make test
make quality-regression
make python-support-test
```

For checkout paths containing spaces, set `CARGO_TARGET_DIR` to a directory
without spaces for the jemalloc build. `make test` runs the
[91 original upstream cases](tests/upstream_legacy/README.md) separately.
The [quality suite](tests/quality/README.md) checks frozen numerical outcomes,
including known limits. Compare the [recorded accuracy and storage results](tests/quality/ACCURACY.md)
with the [published-package timing comparison](docs/upstream-1.0.0/performance.md)
when selecting an engine and a storage budget.

## Project information

[Release notes](RELEASE_NOTES_1.0.0.md) · [Source snapshot](UPSTREAM_SNAPSHOT.md) ·
[Publishing](PUBLISH.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) ·
[Code of conduct](CODE_OF_CONDUCT.md) · [Security](SECURITY.md) · [Apache-2.0 license](LICENSE)
