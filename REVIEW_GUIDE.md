# Review guide: tdigest-rs 1.0.0

This PR brings the completed development implementation into G-Research's
distribution as the next major release. It preserves `tdigest_rs` for existing
applications and exposes the modern engine explicitly through `gr_tdigest`.
The [rollout policy](ROLLOUT.md) defers deprecation to a later release and removal
to a future major release after notice. No publication or upstream merge is
performed by the preparation work.

## Before and after

| Area | Published 0.1.0 / original upstream | Proposed 1.0.0 |
| --- | --- | --- |
| Installation and existing import | `tdigest-rs`; `tdigest_rs.TDigest` | Same distribution/import and original engine; modern is a separate explicit import |
| Original numerical behavior | Original Float32/Float64 arithmetic, uint32 weights, historical copy/pickle semantics | Same pinned in-range calculations and wrapper; checked overflow is rejected explicitly |
| Modern capabilities | Not exposed by the original API | Weighted/fractional mass, CDF, checked updates, k-way merges and portable full-state TDIG serialization |
| Rust API | `tdigest_core` | Original package retained at 0.2.0; modern checked API also available |
| Python runtimes | Published wheel predates the current runtime matrix | CPython 3.10–3.15 ABI3; explicit NumPy combinations, optional Polars 1.x/2.x and Polars-free installations |
| Java/JNI | No Java surface in upstream main | `com.gresearch.tdigest`, Java 11 bytecode, independent native ownership, standalone artifact and Scala/Kotlin/Spark examples |
| Original tests | Six test/support files, 91 parametrized cases | Exact bytes in `tests/upstream_legacy/`; inventory/hash checks and separately reported required runs |
| Additional verification | Original test assertions | Exact fixtures, published-state migration, overflow/state validation, cross-language coherence, runtime/wheel/source-archive and accuracy regression gates |

Modern is not a drop-in numerical replacement. The old and modern settings are
not equal memory or accuracy budgets. The [release notes](RELEASE_NOTES_1.0.0.md)
explain modern API/schema changes; [accuracy results](tests/quality/ACCURACY.md)
retain the known statistical tradeoffs and distinguish historical evidence from
current regression checks.

## Source and adaptation audit

The source tree is pinned in [UPSTREAM_SNAPSHOT.md](UPSTREAM_SNAPSHOT.md).
The modern numerical core, Rust/Python numerical adapter and Polars implementation
are unchanged from that tree. Upstream adaptations cover distribution metadata,
the established contribution's Java namespace, platform build policy, release/CI
integration, isolated original tests and review documentation.

## Validation and performance evidence

The final preparation report will record the exact tested commit/artifact hashes,
completed local and CI checks and fresh baseline/candidate timings. No pending
check is a pass. Run the following gates against the actual upstream package:

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
app-backed check. The PR must remain draft until those external gates are resolved.
