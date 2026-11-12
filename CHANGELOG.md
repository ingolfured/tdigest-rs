# Changelog

## Unreleased

* Add grouped Polars digests and CDF queries with shared Rust, Python and Java implementations.
* Preserve the original Python calling convention and support portable TDIG state in capacity mode.
* Rebuild changed delta merges in Rust and return the updated Python digest directly from native mutation methods.

The release notes explain how `delta=` preserves the original Python API and `max_size=` selects the new one. They include grouped Polars examples, Python query timings and a rerun of the original 0.1.0 benchmark. [1.0 release notes](RELEASE_NOTES_1.0.0.md) and [earlier development history](https://github.com/ingolfured/tdigest-rs/blob/980f0be3f795ae703b86bdf3da8c77f2f7ed752b/CHANGELOG.md)
