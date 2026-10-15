# Review the compatibility-preserving refresh

The original API stays the default. `tdigest_rs.TDigest` uses the unchanged
original Python wrapper and original Rust calculations through a PyO3 adapter.
This preserves `delta`, integer weights, dtype behavior, mutation/copy rules,
errors and saved-state reconstruction. The modern engine is opt-in through
`gr_tdigest`; replacing the original arithmetic while promising all identical
old answers and every modern speedup would be contradictory.

Start with `bindings/python/tdigest_rs/lib.py`, the native-name shim alongside
it, `src/upstream_py.rs`, and `src/upstream/PROVENANCE.md`. Three Rust namespace
imports are adapted; pinned calculations are not rewritten. The separate
`tdigest_core` package retains the original public Rust fields and methods.
An old repository-root path dependency still needs an explicit nested path or
package selection; Python test success is not proof of root-path Rust compatibility.

Then review the opt-in modern engine. It fixes weighted endpoints, overlapping
protected edges, single-centroid means, finite cluster-mean bounds, subnormal
query arithmetic, transactional weight scaling and wire-state validation. A nonpositive K2Norm
normalizer now retains existing centroids instead of collapsing high-delta
two-point inputs; positive-domain arithmetic and the original engine are unchanged.
For f32 means, weights are stored as f64 to preserve mass, increasing each
centroid from 12 to 16 bytes. Modern Polars structs use f64 weights while reading
the earlier f32 schema. V3 flag `0x08` marks f32 states requiring f64 weight
storage; readers of the old format reject this extension. V1/V2 cannot silently
discard such mass; cast to f64 or use V3. Query-only subnormal normalization does
not reconstruct information already lost during compression or solve arbitrary
aggregate overflow. No universal best-speed or best-accuracy claim is made.

The regression layers have distinct purposes:

- The original 91 Python cases are copied without edits and run against the
  shipped `tdigest_rs` package, with no test-only replacement module.
- Independent exact-output fixtures cover old f32/f64 construction, weighted
  input, merges and queries; dedicated original Rust tests cover its public API.
- Thirty-two genuine published-pickle fixtures come from PyPI **0.1.0**. The
  preserved source revision is **0.2.0**. The old loader recompresses using its
  default delta; preserving it means comparing restored old states, not assuming
  pre-pickle centroids are unchanged. NumPy 2 protocol-5 pickles may not load on
  NumPy 1 because of NumPy's module namespace; that rollback limitation is not
  a numerical difference introduced by the digest.
- Installed-artifact gates check imports outside the checkout, original/native
  identities, dependency metadata, no-Polars installation and source archives.
  Two upstream-specific version regressions ensure `gr-tdigest` metadata cannot
  supply this distribution's public version.

The transplant source is private commit
`360ad5b9dcd8b133a40cea9b6b70a83ba390e7fa`, with the metadata gate correction
`3d0182a5713be0d1835296a8c7a340c987243072` and K2Norm fix
`ff73cfab31d6368d203c1a361b8efaaea29d735b`. Original upstream is pinned at
`8d9cf1fe82c5c9254e5dc9593f01717e317f4333`; current upstream
`32a49203d6fdbc80e3ea4a381265e83762f87faa` changes only workflows relative to that
pin. Its numerical/API files are identical. Historical private validation and
benchmarks remain evidence for their named sources/artifacts, not this new
distribution/version/platform adaptation. Fresh results belong here only after
the adapted candidate is built and checked.

The declared support range is CPython 3.10–3.12 and NumPy `>=1.26.4,<3`; the
modern Polars extra is optional and pinned to tested version 1.34.0. The seven-cell
gate expects 208 compatibility cases in each cell, plus 92 modern cases in each
full cell or 28 NumPy-only cases without Polars. These are test selections, not
results for an unbuilt candidate. The upstream matrix retains Linux GNU/musl,
macOS Intel/ARM and Windows configurations. Our local execution remains Linux.

The upstream distribution name is `tdigest-rs`. Both namespaces are bundled in
one wheel so a same-name pip upgrade can remove the old native module and select
the new shim. Private `gr-tdigest` must not be co-installed: it shares those file
paths, and uninstalling one owner can remove the other's files. Root version
`2.0.0`, any crates.io publication, a unique modern namespace, Linux compatibility
tags and the final release decision remain explicit rollout matters.
