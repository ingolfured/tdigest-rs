# tdigest-rs

Start with the [maintainer before/after review guide](REVIEW_GUIDE.md).

This upstream 1.0.0 contribution contains the completed 0.3.0 implementation from
the personal development repository. See [snapshot provenance and upstream
adaptations](UPSTREAM_SNAPSHOT.md), [release notes](RELEASE_NOTES_1.0.0.md) and
[the upstream release procedure](PUBLISH.md). The [migration guide](ROLLOUT.md) describes both Python constructor modes.

The [untouched original suite](tests/upstream_legacy/README.md)
is a separate required compatibility gate.

For the upcoming 1.0.0 release, read the [release notes and upgrade guide](RELEASE_NOTES_1.0.0.md)
covering the changes from 0.2.x.

Java builds cover JDK 11, 17, 21 and 25 while targeting Java 11 bytecode.
JDK 25 uses Gradle 9.1; the default Gradle 8.14.5 retains JDK 11 build support.
An optional checksum-verified JDK and
Gradle bootstrap supports internal URLs or local archives. Configure
`TDIGEST_JDK_URL`, `TDIGEST_GRADLE_URL` and an exclusive
`TDIGEST_MAVEN_REPOSITORY_URL`; use `TDIGEST_OFFLINE=1` with prepared caches.
See [Java setup and offline builds](bindings/java/README.md) for all environment
settings and actual Java11 bytecode/runtime checks.

T-Digest provides a mergeable summary of a distribution, enabling approximate quantiles and CDF with strong tail accuracy.
`tdigest-rs` ships one Rust core with Rust, Python, Polars, and Java surfaces.

## ✨ Features
- 🦀 Single Rust core shared across Rust, Polars, Python, and Java.
- 🚀 Mergeable digests for large and streaming data with fast union and consistent accuracy.
- 🔁 Cross-surface coherence: consistent, verified behavior across all bindings.
- ⚡ Quantile, CDF, and median with optimized evaluation loops using half-weight bracketing and singleton-aware interpolation.
- 🧠 Heap-stream k-way digest merge in Rust core for lower peak memory on large digest unions.
- 🧵 Streaming two-way raw-ingest merge path in Rust core (centroids + values) to avoid extra merge buffers.
- 🧊 Mean/value precision as `f64` or `f32`, with `auto` selection where supported; modern centroid weights stay `f64` in both modes to preserve accumulated mass.
- ⚖️ Weighted ingest across Rust/Python/Polars/Java (`add_weighted`, `add_weighted_values`, Java weighted adds).
- 🔄 Explicit precision casting across surfaces (`cast_precision` / `castPrecision`).
- 📦 TDIG v3 wire default (flags + header length + precision code + checksum), with v1/v2 decode compatibility.
- 🧭 Explicit wire-version encode controls (`to_bytes(version=1|2|3)`, `toBytes(version)`).
- 🖥️ Rust CLI subcommands (`build`, `quantile`, `cdf`, `median`) with `text|csv|json|ndjson` ingestion.
- 🎚️ Scale families: `Quad`, `K1`, `K2`, `K3`.
- 🔩 Singleton handling policy: edge-precision (`keep N`), respect singletons, or uniform merge.

## Historical comparison with the original G-Research engine

In the historical comparison, At matched logical centroid-field byte budgets, it wins average rank error in **279/324** recorded real-data cases, tail rank error in **295/324**, and average value error in **260/324**. It also provides CDF queries, fractional weights, portable TDIG state and a shared Rust/Python/Polars/Java core.

For a Bike single build at size 128, Modern has about **0.017 times GR's average rank error** and **0.035 times its average value error**. Energy also favors Modern on average accuracy, while GR has lower peak value error. See [why choose Modern](comparison_design.md) for the recommendation and [setup tables](compat/quality-20261020/RESULTS.md) for the full comparison, including cases GR wins.

For the 21 October 2026 comparison of original delta 300 and modern capacity
1,000, see [accuracy results and tradeoffs](tests/quality/ACCURACY.md).
The report separates position, numerical-value and storage results and
identifies the historical build measured.

## Examples

**Python**
```python
import tdigest_rs as td

d = td.TDigest.from_array([0, 1, 2, 3], max_size=100, scale="k2")
print("p50 =", d.quantile(0.5))
print("cdf =", d.cdf([0.0, 1.5, 3.0]))
```

**Polars**
```python
import polars as pl
from tdigest_rs import tdigest, quantile

out = (
    pl.DataFrame({"g": ["a"] * 5, "x": [0, 1, 2, 3, 4]})
    .lazy()
    .group_by("g")
    .agg(tdigest("x", max_size=100, scale="k2").alias("td"))
    .select(quantile("td", 0.5))
    .collect()
)
print(out)
```

**Rust CLI**
```bash
# 1) Load numbers from CSV and save a digest
# numbers.csv
# value
# 0
# 1
# 2
# 3
target/release/tdigest build \
  --input numbers.csv \
  --input-format csv \
  --input-column value \
  --to-digest model.tdig

# 2) Read the digest and query quantiles
target/release/tdigest quantile \
  --from-digest model.tdig \
  --p 0.5,0.9,0.99 \
  --no-header
```

**Java (AutoCloseable)**
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

## Project layout
```text
├── src/                                  # Rust core, CLI, algorithm modules
│   ├── bin/                              # tdigest CLI
│   └── tdigest/                          # Core T-Digest implementation
├── bindings/
│   ├── python/                           # Python package + tests
│   └── java/                             # Java API (Gradle) + JNI bridge
├── integration/
│   └── api_coherence/                    # Cross-surface contract tests
├── crates/
│   └── testdata/                         # Fixtures
└── dist/                                 # Built artifacts after release
```

## Quick Development Start
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

## Publishing
- Publishing and release workflows are documented in `PUBLISH.md`.

## Versions and compatibility
- Weighted medians use centroid mass. TDIG v3 and Polars round-trips retain compression configuration and centroid kind.
- Delta-mode export requires TDIG v3; older formats cannot retain delta.
- Rust: 1.95.0 (pinned; edition 2021)
- Python: CPython 3.10–3.15 (standard GIL builds, ABI3 wheels built with maturin); development tools default to 3.12
- NumPy: 1.26.4 or the 2.x line; tested combinations are recorded in `scripts/test_python_support.py`
- Polars: optional; install `tdigest-rs[polars]` to install Polars when needed. Existing Polars 1.x or 2.x installs are retained (`polars>=1.0.0`, no upper cap); development uses 1.44.2

Polars integration is isolated in an internal adapter behind the existing public functions. Numerical imports remain usable without Polars installed.

Import `TDigest` from `tdigest_rs` for both modes. The original calling convention
uses `delta=` (default 300). It accepts Float32 and Float64 NumPy arrays, ignores
NaNs, retains infinite endpoints and returns a new digest from merge and update.
Pass `max_size=` for capacity-based compression, strict finite inputs, fractional
weights, CDF, in-place updates and TDIG serialization. Supply one sizing parameter
per constructor. Both modes use the same Rust core for finite data.

Compression, interpolation and restored-pickle queries use modern numerical
results. For example, the 10th percentile of `[1.0, 2.0]` changes from 0.7 to
1.0, and the median of `[0, 10]` with weights `[90, 10]` changes from 1 to 0.
Published 0.1.0 pickles carry centroid means and weights. Loading one reconstructs
a digest from those observations.

The unchanged upstream Python suite runs in `make test` and Linux CI. `make python-support-test` builds one release Linux wheel from the verified source archive on Python 3.10 and tests it outside the checkout on Python 3.10–3.15, with both NumPy lines on 3.10–3.12 and NumPy 2.x on newer runtimes. Each Python version also gets a Polars-free installation cell. Cargo dependency artifacts are reused; the gate compiles the archive once instead of rebuilding the same ABI3 extension for each build interpreter. See [legacy compatibility](compat/python-modes.md).

CI installs development dependencies before `make build` compiles the package.
Installed-wheel and source-archive compatibility run in a separate job alongside
the main build, unit tests and accuracy checks. The package tests also check
that source archives contain the accuracy tests, saved results and offline data.
The source-archive build reuses the checkout's Cargo target directory (or an
explicit `CARGO_TARGET_DIR`). One genuine ABI3 wheel is built from the extracted
source archive and checked on every supported runtime. `make python-support-test`
streams compiler progress and retains
per-command timings and logs in `build/python-support/`; CI uploads these even
when a run fails or is cancelled.

## Changelog
- Read the [1.0.0 release notes](RELEASE_NOTES_1.0.0.md) for the upcoming release and [CHANGELOG.md](CHANGELOG.md) for version history.

## Future improvements
- Auto suggest a scaling function based on distribution.

## Community
- Contributing guide: `CONTRIBUTING.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- Security policy: `SECURITY.md`
- Issues: https://github.com/G-Research/tdigest-rs/issues

## License
- Apache-2.0


### Rust crate

The root Cargo package is `tdigest-rs` and its library is `tdigest_rs`. Migrate original Rust callers to the checked builder API.

When a query returns an ndarray, it is an independent writable Float64 snapshot with ordinary NumPy ownership and resizing behavior. Centroid means and weights are also independent Float64 snapshots. One-dimensional NumPy probes retain an array result, including one element; zero-dimensional probes return scalars. Multidimensional probes are rejected.

The NumPy output conversion measurements and their scope are recorded in [the validation note](https://github.com/ingolfured/gr-tdigest/blob/5801881075c6e31fec746c8c62c6a25782b6c13f/compat/performance/numpy-output-20261015/README.md).

Polars digest structs with delta require K2Norm scale and singleton policy Off, as binary digests do. Incompatible structs return a configuration error when read for queries or serialization.

Modern `TDigest.from_array` and `TDigest.from_means_weights` release the Python GIL during Rust construction after copying input into owned vectors. Independent constructors can therefore run in a caller-managed thread pool. Python input conversion still holds the GIL, and the library does not create a separate constructor pool.

Modern training and updates copy compatible aligned, native-endian contiguous one-dimensional NumPy Float32/Float64 buffers directly into owned Rust vectors. Read-only arrays are supported; strided, unaligned, byte-swapped, scalar and other-dtype inputs retain their generic conversion path. Input storage is neither retained nor mutated.

## Accuracy on recorded data

`make test` now includes fast quality checks using recorded bike-rental and household-energy data, varied distributions and exact weighted references. `make quality-extended` measures full datasets, both precisions, several summary sizes and 40-way merges. It retains failing profiles and reports percentile position, value and cumulative-probability errors separately.

The recorded comparison is legacy/original G-Research versus the opt-in Modern engine at matched logical centroid-field byte budgets. It measures accuracy on these workloads; it does not establish a universal replacement for legacy, a speed ranking or equal process memory use. The figures below come from CI run 104 at `e6a14a2`, rather than a fresh measurement of the current branch.

The modern engine is not universally more accurate than original G-Research:

- **Bike:** Modern wins average rank, tail rank, average value and peak value error in every grouped size/merge setup tested.
- **Energy:** Modern wins average rank, tail rank and average value error. GR wins peak value error: Modern's error is **1.81–1.86 times GR's** across the grouped setups.
- **Synthetic distributions:** GR wins all four grouped metrics on Gaussian, exponential, lognormal, Pareto, bimodal and signed-scale data. Modern wins all four on drift, skewed two-point and zero-inflated data; rounded ties and uniform grids split by metric.

These conclusions average cases within each setup; individual cases can differ.

See the [winner and error-ratio tables](compat/quality-20261020/RESULTS.md) for each summary size and merge setup. Every ratio is **Modern error ÷ GR error**: below 1 favors Modern; above 1 favors GR. The [comparison document](comparison_design.md#modern-versus-original-gr-measured-accuracy-ci-21-october-2026) records the positioning and limits; the [test methods](tests/quality/README.md) define the metrics. `make quality-regression` protects recorded outcomes while preserving known accuracy failures.

The configured JDK also supplies the direct Java compiler/runtime subprocesses used by `make test`; an environment-selected JDK does not require a separate system Java installation.

## Consumer APIs and delivery

Use the [Python/NumPy guide](bindings/python/OBJECT_API.md), [Polars guide](bindings/python/POLARS_API.md), and [Java build and runtime guide](bindings/java/README.md). Scala/sbt, Kotlin/Gradle and a separate-executor Spark check are in [the JVM examples](bindings/java/examples/README.md).

Modern Rust construction returns a checked result, for example `TDigest::<f64>::builder().max_size(1000).build()?`. Modern defaults use capacity 1,000.

The upcoming release is `1.0.0` for Rust, Python and the JVM. Python and Gradle derive their package versions from the root `Cargo.toml`. See the [publishing guide](PUBLISH.md) for release prerequisites.

When migrating modern callers, handle checked Rust construction and conversion results, use the documented NumPy query shapes, and account for the updated Polars struct schema. The [Python/NumPy guide](bindings/python/OBJECT_API.md) and [Polars migration guide](bindings/python/POLARS_API.md) describe these changes.

## Measured summary-size tradeoffs

`make quality-budgets` separately measures 4,140 capacity/scale/data/merge profiles,
including explicit 200/1,000 sizes and additional deterministic shapes. It is a
slower diagnostic and returns failure for the observed accuracy failures. Small
summaries remain a numerical acceptance issue; changing the scale does not
universally fix them. K2 remains the default scale for capacity mode. See the [accuracy investigation and recommendation](https://github.com/ingolfured/gr-tdigest/blob/5801881075c6e31fec746c8c62c6a25782b6c13f/compat/consumer-20261020/accuracy-investigation/REPORT.md).

JVM builds accept a selected native file with any basename through
`TDIGEST_NATIVE_FILE`. Packaging renames it to the native loader's canonical
resource path, removes stale generated payloads and verifies the finished JAR.
CI exercises a renamed override and runs that JAR outside the checkout.

Modern Rust builders, seeded construction, merges and explicit precision conversions return checked results. Malformed reconstructed state is rejected before use.
Validation includes numerical consistency between aggregate statistics and centroids, within floating-point rounding limits. It does not prove the original data or statistical accuracy. Positive scaling validates independent candidate state before replacing the receiver.

Overflow protection covers modern construction, reconstruction, updates, merges
and positive scaling through the shared Rust core used by Python, Polars, Java
and the CLI. Unsupported aggregate or selected-precision results return errors;
failed updates preserve the receiver. CDF/quantile interpolation avoids extreme
finite endpoint overflow; trimmed means normalize overflowing moments before
averaging. Ordinary floating-point rounding and statistical approximation remain.

The Python delta adapter checks the total weight fits in uint32.

Java object restoration owns an independent native handle; builder and ownership contracts are covered by the Java consumer regression tests. See the [Java guide](bindings/java/README.md).

Capacity tuning counts trial clusters without building discarded centroids; final compression and public numerical settings retain their existing behavior.
