# Untouched original upstream suite

`bindings/python/tests/` contains the complete original G-Research Python suite:
**91 test cases**, six Python test/support files, with **no source edits**.
`bindings/python/benchmarks/run.py` is the unchanged original benchmark.

The original directory layout is retained below this folder so every file maps
directly to its upstream path. [manifest.json](manifest.json) records the source
repository, exact commit, original paths and SHA-256 hashes; [PROVENANCE.md](PROVENANCE.md)
provides the human readable provenance. The tests at pinned commit
`8d9cf1fe82c5c9254e5dc9593f01717e317f4333` also match upstream `main` at
`32a49203d6fdbc80e3ea4a381265e83762f87faa` byte for byte.

Run `make compat-test`, or the full `make test`. The external launcher
`scripts/test_upstream_legacy.py` checks the entire snapshot inventory and hashes,
copies the original suite to an isolated temporary directory, runs it against the
installed package, and requires exactly 91 passed cases with no skips or xfails.
Its separate report is `build/ci/upstream-legacy.xml`. No launcher/configuration
adaptations are embedded in the copied tests.

The installed wheel runtime matrix and across platforms interface jobs run this
same suite separately from the additional compatibility and modern tests. Source
archives must contain the same test bytes and provenance. Do not regenerate
expected answers, reformat these files, filter out cases or edit their assertions
to accommodate a changed engine. An upstream snapshot update requires an explicit
review of the source revision, complete inventory and checksum changes.
