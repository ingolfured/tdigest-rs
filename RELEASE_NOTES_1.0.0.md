# 1.0.0 release notes

**Status: unreleased.** This proposes the next major upstream release after
published 0.1.0 (upstream source metadata 0.2.0). The implementation comes from
the completed personal-repository 0.3.0 snapshot; modern API migration notes
below compare with that project's earlier 0.2.x development line.

The original Python import and delta calling convention continue on a single Rust engine. See [the migration guide](ROLLOUT.md).

1.0.0 is a substantial correctness, compatibility and usability update to
tdigest-rs. It improves weighted statistics and saved state, makes invalid
operations fail safely, and brings the Python, Polars and JVM interfaces into
closer agreement with the Rust core. It also includes API and schema changes
that existing modern-engine applications need to account for when upgrading.

The modern Rust crate, Python package and JVM artifact use version 1.0.0.
The standalone `tdigest_core` crate is removed from the workspace.

## Native Polars expressions

Use `tdigest` in a lazy `group_by().agg()` to build a digest for each group.
Query the results with `quantile` and `cdf`, or merge digests across partitions
with `merge_tdigests`. The [Polars guide](bindings/python/POLARS_API.md)
shows how to compute percentile ranks after joining digests back to the input.

## More reliable weighted statistics

Weighted medians and quantiles now consistently account for observation weights,
including fractional weights. Fixes cover interpolation near the tails, exact
single-value summaries, very small total weights, and compression that previously
lost a trailing contribution at small capacities. More careful summation also
improves calculations when large positive and negative values cancel.

Modern summaries retain weights, total weight and weighted sums in Float64,
even when means are stored in Float32. This prevents weights from being rounded
away merely because Float32 storage was selected. It increases storage for
Float32 centroids; it cannot restore information already lost in an older digest.

## Safer updates and saved state

Construction, reconstruction, merging, precision conversion and positive scaling
check that the resulting digest is valid. Unsupported arithmetic and inconsistent
saved state produce errors. A failed modern update, merge or scaling operation
leaves the existing digest unchanged, including an iterable merge whose later
input is invalid.

Modern Python copies, pickle restoration and TDIG binary round trips preserve
independent full state: weights, extrema, weighted sum, compression settings and
the distinction between exact points and compressed groups. Rebuilding from
`means` and `weights` alone still constructs weighted observations; it is not a
full-state copy.

TDIG v3 retains the added configuration and weight information. Existing v1/v2
data remains readable, but older formats cannot express every modern state.
Exports that would lose unsupported state are rejected. Older readers may also
reject newly used v3 flags, so check readers before exchanging new saved data.

## Original G-Research compatibility

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

## Python and Polars improvements

Modern Python construction now honors supplied weights. Copies own independent
state, and installed type declarations and method documentation make the API
easier to use from editors and type checkers.

Compatible NumPy input and output buffers use bulk copies. Independent modern
constructors release the Python interpreter lock during native construction,
allowing a caller's thread pool to build separate digests concurrently. Input
conversion still holds the lock; sharing one mutable digest between threads is
not supported.

Polars is optional. Numerical Python use does not require it, and installing
`tdigest-rs[polars]` retains an already installed compatible Polars version.
Compatibility checks cover selected Polars 1.x releases and 2.0.0. CDF operations
now match digests and probes by row count, preserve List-shaped results, and keep
valid empty digests distinct from missing rows.

## Faster capacity searches

When compression exceeds the centroid capacity, trial passes now count clusters
without allocating temporary centroid vectors or computing means that would be
discarded. The selected final pass retains its existing numerical arithmetic.
This reduces work for builds and merges that need capacity tuning; paths that
skip that search do not receive the same benefit.

## JVM delivery

Java gains completed weighted/delta builders and fluent operations. Deserialized
objects own independent native handles, fixing premature cleanup of restored
state. Catchable Rust panics are translated to Java exceptions. Packaged JARs
load their native library outside a development checkout and provide clearer
loading diagnostics. Scala, Kotlin and separate-executor Spark examples cover
use of the shared Java artifact.

JVM builds support configured toolchain/dependency sources and offline operation
after dependencies have been staged. They target Java 11 bytecode.

## Upgrading from 0.2.x

| Area | What to check in your application |
| --- | --- |
| Modern Rust API | Builders, seeded construction, merges and precision conversions return checked `Result` values. Handle errors, for example with `builder().build()?`. The configuration name is `delta`, replacing `legacy_delta`. |
| Defaults and delta | For capacity mode in Python, pass `max_size=1000` explicitly. Omitting both sizing arguments selects `delta=300`. Modern delta mode uses K2Norm with singleton policy Off; incompatible explicit settings are rejected. |
| NumPy query outputs | Scalar and zero-dimensional probes return scalars. One-dimensional arrays return independent writable Float64 arrays, including single-element inputs. Lists and tuples retain their containers. Flatten and reshape multidimensional probes in your application. |
| Polars schemas | New structs include compression settings and centroid kind; weights are Float64 in both mean precisions. Review explicit schemas and persisted struct columns. Older six-field structs are read using their historical defaults. |
| Polars missing rows and CDF | Missing digest rows are errors. Supply a genuine empty digest when that is intended. CDF broadcasting follows row counts, and List probes retain List output. |
| Binary decoding | Give column-based Polars `from_bytes` an explicit `precision="f32"` or `"f64"`. This checks the encoded precision; it does not cast the digest. |
| Saved state | Use full-state copies or TDIG v3 for faithful modern restoration. Delta and other newly represented settings may require v3. Check compatibility with older consumers before writing new state. |
| Invalid operations | Expect errors for malformed state, unsupported numeric ranges, or merges with differing precision or compression settings, including empty contributors. |

See the [Python/NumPy guide](bindings/python/OBJECT_API.md),
[Polars guide](bindings/python/POLARS_API.md),
[Rust API contract](api_design.md) and [Java guide](bindings/java/README.md)
for detailed behavior and examples.

## Runtime and build support

- Python: standard CPython 3.10–3.15. NumPy requirements depend on the Python
  version; Python 3.13 and later require NumPy 2.x. See the
  [package requirements](bindings/python/pyproject.toml).
- Polars: optional, with a declared minimum of 1.0.0. The installed-package checks
  cover 1.0.0, 1.20.0, 1.38.1, 1.44.2 and 2.0.0. An open dependency range does not
  establish compatibility with every future version.
- JVM: build/runtime coverage for JDK 11, 17, 21 and 25, targeting Java 11 bytecode.
- Rust source builds: the repository pins Rust 1.95.0.
- Linux wheel compatibility is recorded in each wheel’s platform tag. The source-archive test builds a manylinux_2_28 wheel.

## Accuracy and validation

The test suite now includes independent original-engine reference outputs,
weighted numerical controls, recorded-data accuracy cases, cross-language saved
state checks and installed-package tests. Source archives and standalone JARs
are checked as consumer artifacts as well as testing the checkout.

T-digest remains an approximation. Accuracy depends on the data, summary size,
scale and merge pattern; known difficult cases remain, particularly with small
summaries. Modern does not win every accuracy measure against the original
engine. The [comparison guide](comparison_design.md) explains those tradeoffs,
and the [quality test guide](tests/quality/README.md) describes the reproducible
checks. Historical development timings are not a general speed or memory
guarantee for 1.0.0.

Publication and final release validation are tracked in the
[publishing guide](PUBLISH.md).
