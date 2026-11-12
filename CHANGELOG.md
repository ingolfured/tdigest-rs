# Changelog

## Unreleased

* Add grouped Polars digests and CDF queries with shared Rust, Python and Java implementations.
* Preserve the original Python calling convention and support portable TDIG state in capacity mode.
* Filter unweighted NumPy input in Rust and merge sorted centroids directly when changing delta.

The release notes explain how `delta=` preserves the original Python API and `max_size=` selects the new one. They compare accuracy and Python query speed at equal centroid counts and give the setup for each benchmark. [1.0 release notes](RELEASE_NOTES_1.0.0.md) and [earlier development history](https://github.com/ingolfured/tdigest-rs/blob/980f0be3f795ae703b86bdf3da8c77f2f7ed752b/CHANGELOG.md)
