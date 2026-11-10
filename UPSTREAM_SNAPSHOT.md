# Source provenance

The shared Rust implementation was imported from the
[development repository at `0eaa794`](https://github.com/ingolfured/gr-tdigest/commit/0eaa79411d1ca46cd0cf7294b03b6aafaf1a120c).
The [original Python suite](tests/upstream_legacy/PROVENANCE.md) is preserved
separately with its upstream paths and hashes.

The Cargo and Python distributions use `tdigest-rs`, with `tdigest_rs` as the
Python import. The JVM artifact uses `com.gresearch.tdigest:tdigest-rs`.
See the [migration guide](ROLLOUT.md) for Python API changes and the
[publishing guide](PUBLISH.md) for the upstream release process.
