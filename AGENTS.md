# Working on tdigest-rs

Read `api_design.md` and `tdigest_design.md` before changing numerical behavior. The Rust library supplies the compression, quantile and CDF implementations used by Python, Polars, Java and the CLI.

## Build and test

Run `make setup` to prepare the development environment. Run both commands from the repository root before submitting changes.

```sh
make build
make test
```

The test target runs the Rust and Java tests, the Python and Polars integration tests, and the 91 original Python cases. The original files and benchmark under `tests/upstream_legacy/` have pinned hashes. Add new expectations to the current test suite.

`make lint` runs the formatters, Clippy, Python checks and Rust documentation build. The formatters can edit files.

## Where to make changes

* `src/tdigest/` contains the core. Keep centroid means strictly ordered and preserve total mass and observed extrema. Means and extrema use the selected precision. Weights, weighted sums and total mass use Float64. Check both interpolation and serialization when changing the distinction between atomic and mixed centroids.
* `src/tdigest/frontends.rs` contains shared configuration, validation and merge rules. The bindings translate inputs and errors. Keep existing public error wording where callers rely on it.
* `bindings/python/tdigest_rs/lib.py` selects the Python calling convention. The default and `delta=` preserve the original API. `max_size=` selects capacity mode. Both use the Rust core for finite observations.
* `src/py.rs` binds the Python object. `_modern.py` wraps the capacity API and `_polars.py` builds expressions. `__init__.py` exports the public names. Numerical imports must work without Polars installed.
* `src/polars_expr.rs` implements the Polars expressions. The planned schema must match the result at execution. Float32 input selects Float32 means. Check nulls, empty groups, broadcast probes and explicit precision when reading TDIG bytes.
* `src/jni.rs` and `bindings/java/src/com/gresearch/tdigest/` implement the Java binding. Invalid inputs raise `IllegalArgumentException`. The loader checks the explicit native path, then the bundled resource. When no resource is present it tries the Java library path and finally the checkout.
* `src/bin/tdigest_cli.rs` implements `build`, `quantile`, `cdf` and `median`. Keep CSV headers and columns compatible with existing consumers.
* `integration/api_coherence/` compares results across the CLI, Python, Polars and Java. Update the relevant tests when changing their public behavior.

## Numerical and performance checks

The Python delta adapter skips NaNs and retains infinite endpoints. Capacity mode requires finite training values. Strict binding quantile calls reject probabilities outside the unit interval. The raw Rust quantile clamps them. For an empty digest, CDF returns NaN. An empty capacity quantile returns NaN in Python and null in Polars. Merging digests with different storage precision requires an explicit cast.

Common workloads merge about 40 digests at a time. Sample counts range from empty to millions, and a process may retain millions of digests. Measure memory and accuracy alongside time, especially for CDF and median queries. Keep automatic tuning optional and measure its overhead. If a local `typical_usecase.md` is available, consult it for production assumptions.

## Preparing a change

Keep related code, tests and documentation together. Run the relevant binding tests during development and the two repository commands above on the final change. Update the README and design documents when behavior changes. Update `comparison_design.md` when published comparisons change. Numerical and performance claims should identify the input, baseline and settings.

Every commit needs a staged update to the root `CHANGELOG.md`. Use actual newlines in commit messages. Move release notes out of the unreleased section before pushing a release tag.
