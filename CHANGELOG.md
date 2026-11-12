# Changelog

## Unreleased

* Add grouped Polars digests and CDF queries with shared Rust, Python and Java implementations.
* Preserve the original Python calling convention and support portable TDIG state in capacity mode.
* Rebuild changed delta merges in Rust and return the updated Python digest directly from native mutation methods.
* Introduce the library with a concise feature list covering Float16 input and parallel CDF queries, followed by runnable Python, Polars, Rust, CLI, and Java examples. Document the legacy Python API separately.

See the [1.0 release notes](RELEASE_NOTES_1.0.0.md) for compatibility cases, measurements and reproduction commands. [Earlier development history](https://github.com/ingolfured/tdigest-rs/blob/980f0be3f795ae703b86bdf3da8c77f2f7ed752b/CHANGELOG.md)
