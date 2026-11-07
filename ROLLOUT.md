# Major release and legacy API policy

## 1.0.0: introduce the modern engine while retaining the original path

The published G-Research distribution is `tdigest-rs` 0.1.0; upstream source
metadata is 0.2.0. This contribution proposes the next major release, **1.0.0**.
The development repository's 0.3.0 implementation is the source snapshot, not the
upstream release number. Neither a tag nor a publication is performed by this PR.

Existing `from tdigest_rs import TDigest` applications continue to select the
original engine. Original in-range calculations, API, dtype rules, uint32 weights
and historical copy/pickle behavior remain supported. Explicit overflow guards
reject invalid totals or finite-input arithmetic overflow; that deliberate
boundary is documented and tested. Existing callers are never silently routed
through the modern engine. No new legacy deprecation warning is introduced.

New applications can explicitly choose `from gr_tdigest import TDigest` for the
modern engine. Its numerical answers and state format differ; matching `delta`
does not establish equivalent results. The original `tdigest_core` Rust package
remains 0.2.0; the new root distribution and JVM artifact use 1.0.0.

The untouched [original test suite](tests/upstream_legacy/README.md), exact-output
fixtures, public API contracts and real published-pickle migration checks are
required compatibility gates. Release approval requires passing results from the
actual upstream package, not only the development distribution.

## Later release: announce and support deprecation

Deprecation is a separate maintainer decision in a later release. Before enabling
warnings or changing support status, publish migration instructions, describe
numerical/API/state differences, identify supported replacement operations and
announce the intended removal major version with a meaningful notice period.
Continue running the original suite and supporting existing users during that
period. This PR does not choose a deprecation date or release number.

## Future major release: consider removal after deprecation

Removal is permitted only in a future major release after the announced
deprecation period, with explicit maintainer approval, release notes and a
documented saved-state migration/support policy. It must not happen implicitly
through a dependency update, import alias, default change or compatibility-test
deletion. This PR does not remove the old path or schedule its removal.
