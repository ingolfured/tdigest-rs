# tdigest-rs

A t-digest summarizes a distribution so you can estimate quantiles, medians and
cumulative probabilities without retaining every observation. This project
provides native Polars expressions for grouped aggregation and CDF queries in
lazy DataFrames, alongside a Rust library and CLI, Python objects and Java bindings.

## Python installation

```bash
pip install tdigest-rs
# Include Polars for DataFrame expressions
pip install 'tdigest-rs[polars]'
```

Import `TDigest` from `tdigest_rs`. Pass `delta=` for the original Python
calling convention, or `max_size=` for capacity-based compression, fractional
weights, CDF queries and portable binary state. Omitting both selects the
original default of `delta=300`. Both modes use the same Rust implementation.
The [1.0 migration guide](ROLLOUT.md) describes the numerical changes and how
previously saved Python digests are loaded.

## Examples

### Polars

Compute each request’s percentile within its service. Build one digest per
service, join it back to the requests, then evaluate the CDF at each latency.

```python
import polars as pl
import tdigest_rs as td

requests = pl.LazyFrame({
    "service": ["search", "search", "checkout", "checkout"],
    "latency_ms": [12.0, 48.0, 35.0, 90.0],
})
digests = requests.group_by("service").agg(
    td.tdigest("latency_ms", max_size=200).alias("digest")
)
ranked = requests.join(digests, on="service").select(
    "service", "latency_ms",
    td.cdf("digest", pl.col("latency_ms")).alias("percentile_rank"),
)
print(ranked.collect())
```

### Python

```python
import tdigest_rs as td

d = td.TDigest.from_array([0, 1, 2, 3], max_size=100, scale="k2")
print("p50 =", d.quantile(0.5))
print("cdf =", d.cdf([0.0, 1.5, 3.0]))
```

### Rust CLI

```bash
# Build a digest from the value column in numbers.csv
target/release/tdigest build \
  --input numbers.csv \
  --input-format csv \
  --input-column value \
  --to-digest model.tdig

# Query the median and upper quantiles
target/release/tdigest quantile \
  --from-digest model.tdig \
  --p 0.5,0.9,0.99 \
  --no-header
```

### Java

```java
import com.gresearch.tdigest.TDigest;
import com.gresearch.tdigest.TDigest.Precision;
import com.gresearch.tdigest.TDigest.Scale;
import com.gresearch.tdigest.TDigest.SingletonPolicy;

public class Example {
  public static void main(String[] args) {
    try (TDigest digest = TDigest.builder()
        .maxSize(100)
        .scale(Scale.K2)
        .singletonPolicy(SingletonPolicy.USE)
        .precision(Precision.F64)
        .build(new double[]{0, 1, 2, 3})) {
      double p50 = digest.quantile(0.5);
      double[] cdf = digest.cdf(new double[]{0.0, 1.5, 3.0});
      System.out.println(p50 + " " + cdf.length);
    }
  }
}
```

## Language guides

- [Python and NumPy](bindings/python/OBJECT_API.md) covers precision, weights, updates and serialization.
- [Polars](bindings/python/POLARS_API.md) covers expressions, grouped aggregation and binary columns.
- [Java](bindings/java/README.md) covers the JAR, native loading and toolchain setup.
- [Rust API contract](api_design.md) and [implementation notes](tdigest_design.md) describe compression, merging and the TDIG format.

## Development

```bash
make setup
make build
make test
```

Accuracy checks run as individual pytest cases in `make test`. Use
`make quality-extended` for the slow precision/order/merge matrix. Known accuracy
limits appear as expected failures only after their frozen regression checks
pass. `make quality-fast` and `make quality-extended` retain JSON measurements
under `build/quality/`, including failures. See [quality tests](tests/quality/README.md)
for rerunning one profile and generating candidate baselines for review.

Setup supports linked Git worktrees. If the checkout path contains spaces,
set `CARGO_TARGET_DIR` to a build directory without spaces: the bundled
jemalloc build rejects spaces in its installation prefix. The CLI tests and Java
packager respect `CARGO_TARGET_DIR` directly.

## Accuracy and compatibility

The [original Python suite](tests/upstream_legacy/README.md) runs as part of
`make test`. The [1.0 vs 0.1.0 benchmark results](docs/upstream-1.0.0/comparison.md)
cover large-array builds, merges, the original threaded benchmark and quantile
accuracy on recorded data. The [accuracy tests](tests/quality/README.md) compare estimates
with sorted input across precisions, compression settings and merge orders.
The [recorded comparison with the original engine](tests/quality/ACCURACY.md)
includes rank error, value error, storage costs and known limits.

The historical comparison on recorded data measured lower mean rank error in
279 of 324 matched-storage cases and lower tail rank error in 295 of 324.
The [full comparison](comparison_design.md) includes the workloads where the
original engine was more accurate.

See the [release notes](RELEASE_NOTES_1.0.0.md), [changelog](CHANGELOG.md) and
[publishing guide](PUBLISH.md) for release details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), the [code of conduct](CODE_OF_CONDUCT.md)
and the [security policy](SECURITY.md).

## License

[Apache License 2.0](LICENSE)
