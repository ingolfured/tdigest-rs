# 🌀 tdigest-rs

A t-digest is a small, mergeable summary of a distribution. It can answer both “What was the 99th-percentile latency?” and “Where does this 48 ms request rank among requests to the same service?” Build one digest per service or per day, then merge them to estimate quantiles across the whole week.

## ✨ Features

- 🦀 **One Rust core** for Python, Polars, Java, and the Rust CLI. Build a digest in Polars and query the same summary in Python or Java.
- ⚡ **Quantiles, median, and CDF.** Look up a value at a percentile, or pass an array of values to get their percentile ranks in one call.
- 🚀 **Streaming updates and merges.** Add observations as they arrive or combine summaries built on separate partitions. The Rust core can merge several digests by reading their sorted centroid runs together.
- ⚖️ **Weighted observations.** Give a value a fractional weight or use its frequency when your data already contains counts.
- 🧊 **Precision and compression.** Store centroid means as Float32 or Float64. In capacity mode the weights stay Float64. Choose a scale (Quad, K1, K2, normalized K2, or K3) and a singleton policy to control how observations are grouped near the tails.
- 📦 **Portable digests.** TDIG v3 bytes carry the weights, observed extrema, precision, and compression settings. The reader also accepts v1 and v2.

## Install

```sh
pip install tdigest-rs           # Python and NumPy
pip install 'tdigest-rs[polars]' # Include the Polars expressions
```

The Python package supports CPython 3.10 through 3.15.

## ⚡ Quick start

```python
from tdigest_rs import TDigest

d = TDigest.from_array([0, 1, 2, 3], max_size=100, scale="k2")
print(d.quantile(0.5))           # 1.5
print(d.cdf([0.0, 1.5, 3.0]))   # [0.125, 0.5, 0.875]
```

The middle probe falls between 1 and 2, so half the observations lie below it. At an observed value, the CDF counts half of the tied weight.

## Polars

Find the 99th percentile for each service. The aggregation runs in a lazy query.

```python
import polars as pl
import tdigest_rs as td

requests = pl.LazyFrame({
    "service": ["search", "search", "checkout", "checkout"],
    "latency_ms": [12.0, 48.0, 35.0, 90.0],
})
by_service = requests.group_by("service").agg(
    td.quantile(td.tdigest("latency_ms", max_size=200), 0.99).alias("p99")
)
print(by_service.sort("service").collect())  # checkout: 90 ms, search: 48 ms
```

Use `td.cdf("digest", pl.col("latency_ms"))` to rank observations. The [1.0 release notes](RELEASE_NOTES_1.0.0.md) show the join and explain how ties count. Float32 columns produce digests with Float32 means. A list column of probes returns a list per row. A sequence passed directly supplies a vector of probes. For stored TDIG bytes, pass the expected precision to `td.from_bytes` so Polars can plan the output schema.

## Python

Both calling conventions use `from tdigest_rs import TDigest`. Choose `delta=` for code written against 0.1.0 or `max_size=` to set a centroid budget. Version 1.0 uses the same Rust core for both. Some quantiles and weighted medians change when upgrading. The [release notes](RELEASE_NOTES_1.0.0.md) give worked examples.

| | Original calling convention | Fixed capacity |
| --- | --- | --- |
| Constructor | `delta=300` or omit the sizing argument | `max_size=200` |
| Input | Float32 or Float64 NumPy array, NaNs skipped, infinite endpoints retained | Finite values, optional positive weights |
| Precision | Follows the array dtype | Float64 means by default, or choose `precision="f32"` |
| Updates | `merge` and `update` return a new digest | `add`, `add_weighted`, `merge`, `scale_weights` and `scale_values` update the receiver and return it |
| Save | Python pickle or centroid dictionary | TDIG bytes for transfer between languages |

```python
import numpy as np
from tdigest_rs import TDigest

original = TDigest.from_array(np.array([10, 20, 30], dtype=np.float32))
assert original.update(np.array([40, 50], dtype=np.float32)).median() == 30
assert original.weights.sum() == 3

digest = TDigest.from_array([0.0, 10.0], weights=[9.0, 1.0], max_size=200)
assert digest.median() == 0.0
assert digest.cdf(0.0) == 0.45
assert TDigest.from_bytes(digest.to_bytes()).cdf(0.0) == 0.45
```

With `max_size=`, weights, sums and counts use Float64 at either mean precision. Merging requires matching precision and compression settings. Use `cast_precision("f32")` or `cast_precision("f64")` to convert explicitly. A failed update leaves the digest intact. Building from means and weights treats each mean as an observation. Use TDIG bytes when extrema, compression settings and the distinction between a single value and a compressed range must survive.

## Rust and the CLI

Use the `tdigest_rs` crate for the builder and checked merge operations. The CLI can save the digest once and query it later.

```sh
cargo build --release --bin tdigest
printf 'value\n10\n20\n30\n' > numbers.csv
target/release/tdigest build --input numbers.csv --input-format csv --input-column value --to-digest model.tdig
target/release/tdigest quantile --from-digest model.tdig --p 0.5,0.99 --no-header
```

## Java

The JAR uses `com.gresearch.tdigest:tdigest-rs` and bundles the native library for the target platform. Close each digest to release its native memory.

```java
import com.gresearch.tdigest.TDigest;

public class Example {
  public static void main(String[] args) {
    try (TDigest digest = TDigest.builder().maxSize(200).build(new double[]{10, 20, 30})) {
      System.out.println(digest.median());
      System.out.println(java.util.Arrays.toString(digest.cdf(new double[]{10, 20, 30})));
    }
  }
}
```

The Java classes target Java 11. CI exercises JDK 11, 17, 21 and 25. Java 25 uses Gradle 9.1.0 and may need `--enable-native-access=ALL-UNNAMED` at runtime. The [JVM build instructions](bindings/java/README.md) cover offline builds, native loading, Scala, Kotlin and Spark.

## Accuracy on recorded data

What changes if you upgrade and keep `delta=300`? On nine columns of bike-rental and household-energy data, 1.0 had lower average rank error than 0.1.0 in **102 of 108 cases**. All six increases came from outdoor temperature after merging. Eight cases had higher average error in the original units.

The study varied precision, input order, and how the digests were merged. With the same `delta`, 0.1.0 kept 138–272 centroids and 1.0 kept 8–254. The [recorded measurements](docs/upstream-1.0.0/recorded-accuracy.csv) give the counts and errors for each case. The [release notes](RELEASE_NOTES_1.0.0.md) cover the benchmark setup and timings.

Construction and merge costs also differ. On one worker, building from a million shuffled observations took **108 ms in 0.1.0 and 30 ms in 1.0**, producing the same 146 centroids. Merging 2,500 prebuilt pairs on one worker took **140 ms in 0.1.0 and 396 ms in 1.0**. Both timings are medians across three seeds on the same host.

## 🗂️ Project layout

```text
src/                       Rust core and tdigest CLI
bindings/python/           Python package, NumPy API, and Polars expressions
bindings/java/             Java API, JNI bridge, and JVM examples
integration/api_coherence/ Tests that compare answers across language bindings
tests/quality/             Accuracy checks on recorded and synthetic data
benches/                   Rust benchmarks
```

## Development and release

Run `make setup`, `make build` and `make test` from the repository root. The tests include all 91 original Python cases. Run `make quality-regression` for the full accuracy suite and `make python-support-test` for the installed wheel matrix. Use `CARGO_TARGET_DIR` without spaces when building jemalloc. Run `make lint` before submitting changes and include a staged changelog entry with each commit.

The upstream Create release workflow tags the approved version. CI builds and tests the wheels before the release workflow publishes to PyPI. Cargo and Maven publication are separate maintainer actions.

See the [contributing guide](CONTRIBUTING.md), [code of conduct](CODE_OF_CONDUCT.md), [security policy](SECURITY.md) and [Apache 2.0 license](LICENSE).
