# Changelog

## Unreleased

* Add grouped Polars digests and CDF queries with shared Rust, Python and Java implementations.
* Preserve the original Python calling convention and support portable TDIG state in capacity mode.
* Rebuild changed delta merges in Rust and return the updated Python digest directly from native mutation methods.

The release notes show how to upgrade from 0.1.0, rank observations in batches by group, and reproduce the accuracy and timing comparisons. [1.0 release notes](RELEASE_NOTES_1.0.0.md) and [earlier development history](https://github.com/ingolfured/tdigest-rs/blob/980f0be3f795ae703b86bdf3da8c77f2f7ed752b/CHANGELOG.md)
