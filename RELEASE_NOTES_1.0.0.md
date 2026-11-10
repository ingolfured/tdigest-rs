# What’s new in tdigest-rs 1.0

## Native Polars expressions

Which requests were slow for their own service? Build one digest per service,
join it back to the requests, and use the CDF to get each latency’s percentile
rank. The whole calculation runs in a Polars lazy query.

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

Use `quantile` for the reverse question, such as the p99 latency per service.
Digests can also be merged across partitions and stored as binary columns.
Install `tdigest-rs[polars]` for these expressions. Polars is optional for
NumPy users. [Polars expression guide](bindings/python/POLARS_API.md)

## Accuracy and speed compared with 0.1.0

| Using the existing Python API with `delta=` | What we measured |
| --- | --- |
| Quantile accuracy | Lower mean rank error in 102 of 108 cases on bike-rental and household-energy data. Six cases had higher error. |
| Building a digest | Faster at every tested size from 1,000 to 1,000,000 values in both precisions. A million Float64 values took 29.63 ms, down from 110.99 ms (3.75×). |
| Original threaded build-and-merge benchmark | Median runtime rose from 2.561 s to 4.003 s (56% longer). Small builds and sequential merges were also slower in the individual operation benchmarks. |

The comparison includes both wheels, individual timings, per-dataset errors
and commands to reproduce the runs. An earlier study also compares accuracy at
matched storage. [Benchmark results](docs/upstream-1.0.0/comparison.md) ·
[Matched-storage study](compat/quality-20261020/RESULTS.md)

For callers choosing `max_size=`, the K2 capacity search now counts candidate
clusters without allocating intermediate centroids. Against the earlier K2
implementation, merging 40 digests sequentially fell from 18.79 ms to 5.65 ms
and produced identical digest bytes. [K2 benchmark details](docs/upstream-1.0.0/comparison.md#which-operations-got-faster)

## Python, Rust and JVM features

- **Python and NumPy.** Use `max_size=` to set the centroid capacity, query the CDF at an array of values, or update a digest in place. Float32 means can be stored compactly while weights and sums use Float64. Existing callers can continue using `delta=` or its default of 300. [Python object API](bindings/python/OBJECT_API.md)
- **Portable digests.** TDIG v3 carries precision, compression settings, weights, extrema and centroid kinds between Python, Polars, Rust and Java. V1 and v2 remain readable. Use v3 when a digest needs settings the older formats cannot represent. [Wire format and compatibility](tdigest_design.md)
- **Rust and the CLI.** Build, merge and query digests in Rust, or build one from a CSV column with the CLI and reuse it for later quantile and CDF queries. Checked operations report invalid inputs and incompatible merges. [CLI example](README.md#rust-cli) · [Rust API](api_design.md)
- **Java and other JVM languages.** A JAR with native library loading provides weighted construction, merging, quantiles and CDF queries. It targets Java 11 bytecode and includes examples for Scala, Kotlin and Spark. [Java guide](bindings/java/README.md)

Python supports standard CPython 3.10–3.15. Polars tests cover selected 1.x
versions and 2.0.0. For existing consumers, the upgrade guide shows the original
API in use and where numerical estimates change. [Upgrading from 0.1.0](ROLLOUT.md)
