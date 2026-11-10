# Upstream 1.0.0 snapshot

This contribution replaces the earlier PR #38 snapshot with the completed
[`ingolfured/gr-tdigest` master tree at `0eaa794`](https://github.com/ingolfured/gr-tdigest/commit/0eaa79411d1ca46cd0cf7294b03b6aafaf1a120c).
That tree combines the reviewed release work, the final accuracy report (#54)
and the capacity-search optimization (#96). The implementation and its regression
tests are copied as a snapshot, without importing the personal repository's
development history into the upstream PR.

## Upstream adaptations

- The release distribution and root Cargo package are `tdigest-rs`, version 1.0.0.
  The single Python package is `tdigest_rs`, with delta and capacity modes on the shared Rust core.
- Java uses `com.gresearch.tdigest`, matching the existing upstream contribution;
  native JNI symbols, consumer examples and tests use that same namespace.
  Maven coordinates are `com.gresearch.tdigest:tdigest-rs`.
- G-Research's governance files, pinned Actions references, platform wheel matrix,
  required-check mechanism and tag-based PyPI/GitHub release workflow are retained.
  The workflow adapts to the new layout and adds the full cross-language tests.
  All twelve platform/Python interface cells install the actual platform release
  wheel instead of repeating native compilation. The runtime installer is updated
  for stable CPython 3.15; prerelease interpreters are rejected explicitly.
- Jemalloc and its benchmark counters stay restricted to Linux GNU targets.
  Cross-platform packaging leaves wheel platform selection to the upstream build
  matrix; the separate Linux source-archive gate explicitly builds manylinux_2_28.
- Public installation instructions, distribution-version lookup and project
  metadata use the upstream identity. Historical source and measurement links
  continue to identify the revision they actually measured.

Historical snapshot `fa69285` shipped the original engine alongside the modern core. The unified release keeps the original test suite and removes the original crate.

## Review and release

Read [the 1.0.0 release notes](RELEASE_NOTES_1.0.0.md) for API and schema migration,
and [the accuracy report](tests/quality/ACCURACY.md) for measured tradeoffs.
Run `make build`, `make test` and `make python-support-test` against this upstream
tree: evidence from the personal distribution alone does not validate the renamed
upstream package. The cross-platform jobs still need to pass on this PR.

This PR does not publish a release. Version 1.0.0 is proposed; upstream maintainers
control release approval and the existing release workflow described in
[PUBLISH.md](PUBLISH.md).
