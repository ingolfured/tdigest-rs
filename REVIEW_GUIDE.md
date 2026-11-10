# Review guide: tdigest-rs 1.0.0

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

Run `make compat-test` for the 91 original cases and `make test` for the full suite. The original standalone Rust crate and separate Python import have been removed.

## Source and adaptation audit

The source tree is pinned in [UPSTREAM_SNAPSHOT.md](UPSTREAM_SNAPSHOT.md).
The original PR copies the modern numerical core and adapters from that tree.
The proposed follow-up `01529bf` optimizes exact integer-weight K2 capacity trials. Upstream adaptations cover distribution metadata,
the established contribution's Java namespace, platform build policy, release/CI
integration, isolated original tests and review documentation.

## Historical validation and performance evidence

The measurements below came from the earlier two-engine snapshot. They do not measure the unified implementation.

The [validation record](docs/upstream-1.0.0/validation.md) identifies tested
commits/artifact hashes and completed local checks, including all 91 original
tests, 56 installed-wheel runtime cells and a real published-0.1.0 upgrade.
The [fresh performance comparison](docs/upstream-1.0.0/performance.md) reports
absolute timings, seven-sample ranges and storage/accuracy controls for both
precisions, construction, 40-digest merges and queries. In that workload:

- Existing legacy million-value construction improves 3.48–3.92×, with unchanged
  centroid/weight bytes; median and quantile queries regress.
- Modern opt-in provides additional capabilities, but its tested 40×1,000 merge
  workload is about 73–80× slower than published legacy and uses more storage.
- On the follow-up branch, both Python merge methods still fold the 40 inputs
  pairwise. Caching repeated boundary logarithms reduces their 40×1,000 times
  from 18.48–19.49 ms to 5.49–5.55 ms across Float32/64 on matched Linux release
  builds. The original timings above describe the PR before this optimization.
- The extended regression gate passes with **10 known statistical failures**
  still visible as expected failures, not accuracy passes.

Final CI run links and the exact PR head are maintained in the
[PR description](https://github.com/G-Research/tdigest-rs/pull/38). No pending
check is a pass. Reproduce the local gates against the actual upstream package:

```bash
make build
make test
make quality-regression
make python-support-test
```

`make test` includes all 91 untouched original cases and writes their separate
result to `build/ci/upstream-legacy.xml`. The installed-artifact and platform
jobs report the original suite separately from 117 added compatibility cases and
236 modern/package-identity cases. Each original/compatibility run rejects
failures, missing cases, skips and xfails. Accuracy tests retain their documented
known limits; those must not be counted as accuracy passes.

`scripts/test_package_upgrade.py` checks a genuine published 0.1.0 wheel, normal
pip upgrade to the candidate, 32 saved states against the old loader, uninstall
and reinstall. `scripts/benchmark_upstream.py` compares installed published
legacy, candidate legacy and candidate modern paths in alternating processes.
It records absolute timings, sample ranges, centroid storage and rank-error
controls. Source, inputs and artifacts must be identified with the report.

## External checks and release authority

Use the existing GitHub Actions workflow graph; Jenkins is not used for this
project. Required checks now include the full cross-language project in addition
to Rust and Python. The existing G-Research approval and app-backed required-check
mechanism remain intact.

At preparation time, upstream's CI workflow is disabled for inactivity and the
connected account has read-only upstream access. A maintainer must re-enable and
run that workflow. Fork results cannot satisfy the upstream required review or
app-backed check.
