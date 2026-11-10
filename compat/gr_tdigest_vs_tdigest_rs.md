# Original Python API compatibility

`from tdigest_rs import TDigest` selects the original engine. Its Float32
arithmetic, uint32 weights, immutable merge/update, native class names and
default-delta dictionary/pickle reconstruction are part of its compatibility
contract. Finite in-range results retain their original bits. Overflow checks
reject unsupported totals or arithmetic. See [source provenance](../src/upstream/PROVENANCE.md).

`from gr_tdigest import TDigest` selects the modern engine. For example, means
`[0, 10]` with weights `[90, 10]` give a median of 1 in the original engine and
0 in the modern engine. The [release notes](../RELEASE_NOTES_1.0.0.md) cover
migration and modern state formats.

`make compat-test` runs the [unchanged original suite](../tests/upstream_legacy/README.md).
The [exact numerical fixtures](numerical-parity/README.md) also check the
centroids, quantiles and trimmed means in both precisions. Separate
[published pickle fixtures](published-pickle/README.md) check old saved state.
The [review guide](../REVIEW_GUIDE.md) links the installed-package results.
