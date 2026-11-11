# Changelog

## Unreleased

* Trim unused build dependencies and private binding code. The interoperability tests now check both directions of a Python and Polars transfer in the same round trip at each precision.

* Build and query digests in Polars expressions, including a digest per group in a lazy query. CDF evaluates a column of probes against one digest in a single batch.
* Share compression, quantiles, CDF and TDIG serialization across Rust, Python and Java. Capacity mode supports weighted observations and a choice of scale functions. K2 capacity searches reuse rank boundaries for integral weights.
* Keep the `tdigest_rs` import and the existing Python calling convention with `delta=` or its default of 300. All 91 original Python tests run unchanged. The shared core changes some numerical estimates, including queries on reconstructed pickles. The [upgrade guide](ROLLOUT.md) gives examples and documents the seven cases that differ in capacity mode.
* Preserve Float64 centroid weights at both mean precisions, including during merges and casts. Checked operations report inconsistent state or unsupported arithmetic before replacing the digest.
* Support standard CPython 3.10 to 3.15 with optional Polars. Python wheels include type declarations and the Apache license. The JVM artifact bundles the native library. Examples cover Java, Kotlin, Scala and Spark.
* The CLI supports K2Norm, preserves tiny observations in automatic precision mode and reports malformed text or CSV input.
* Accuracy tests check midpoint ranks at ties and the rank between observations. The [comparison with 0.1.0](docs/upstream-1.0.0/comparison.md) includes measurements on recorded data, replay of estimates on identical centroids and the original threaded benchmark.

See the [release notes](RELEASE_NOTES_1.0.0.md) for examples and the [development changelog](https://github.com/ingolfured/tdigest-rs/blob/980f0be3f795ae703b86bdf3da8c77f2f7ed752b/CHANGELOG.md) for earlier development releases.
