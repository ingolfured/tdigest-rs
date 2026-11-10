# Reviewing tdigest-rs 1.0

- Start with the [migration guide](ROLLOUT.md) for the two Python constructor modes and examples of changed numerical results.
- Read the [object API](bindings/python/OBJECT_API.md) for merge semantics, precision and saved state. The [upstream snapshot](UPSTREAM_SNAPSHOT.md) identifies the source revision.
- Run `make build` and `make test` for the Rust, Python and Java builds and tests. `make compat-test` runs just the [91 original Python tests](tests/upstream_legacy/README.md).
- Run `make python-support-test` for the installed-wheel matrix. The [pickle fixtures](compat/published-pickle/README.md) exercise reconstruction from the published 0.1.0 format.
- See the [accuracy tests](tests/quality/README.md) for regression limits and the [historical measurements](docs/upstream-1.0.0/performance.md) for timings from the earlier two-engine revision.
