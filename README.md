# tdigest-rs

Estimate quantiles and percentile ranks without keeping every observation. Build a digest for each group in Polars, update one in Python, or send its bytes to a Java or Rust process. All four interfaces use the same compression and query code.

## Install

```sh
pip install tdigest-rs
pip install 'tdigest-rs[polars]'
```

Use the second command for Polars expressions. The NumPy API works without Polars. The Python package supports CPython 3.10 through 3.15.

## Polars

Find the 99th percentile for each service. The aggregation runs in a lazy query.

```python
import polars as pl
import tdigest_rs as td

requests = pl.LazyFrame({
    "service": ["search", "search", "checkout", "checkout"],
    "latency_ms": [12.0, 48.0, 35.0, 90.0],
})
groups = requests.group_by("service").agg(
    td.tdigest("latency_ms", max_size=200).alias("digest")
)
print(groups.select("service", td.quantile("digest", 0.99).alias("p99")).collect())
```

Use `td.cdf("digest", pl.col("latency_ms"))` to rank observations. The [1.0 release notes](RELEASE_NOTES_1.0.0.md) show the join and explain how ties count. Float32 columns produce digests with Float32 means. A list column of probes returns a list per row. A sequence passed directly supplies a vector of probes. For stored TDIG bytes, pass the expected precision to `td.from_bytes` so Polars can plan the output schema.

## Python

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
    }
  }
}
```

The Java classes target Java 11. CI exercises JDK 11, 17, 21 and 25. Java 25 uses Gradle 9.1.0 and may need `--enable-native-access=ALL-UNNAMED` at runtime. The [JVM build instructions](bindings/java/README.md) cover offline builds, native loading, Scala, Kotlin and Spark.

## Development and release

Run `make setup`, `make build` and `make test` from the repository root. The tests include all 91 original Python cases. Run `make quality-regression` for the full accuracy suite and `make python-support-test` for the installed wheel matrix. Use `CARGO_TARGET_DIR` without spaces when building jemalloc. Run `make lint` before submitting changes and include a staged changelog entry with each commit.

The upstream Create release workflow tags the approved version. CI builds and tests the wheels before the release workflow publishes to PyPI. Cargo and Maven publication are separate maintainer actions.

See the [contributing guide](CONTRIBUTING.md), [code of conduct](CODE_OF_CONDUCT.md), [security policy](SECURITY.md) and [Apache 2.0 license](LICENSE).
