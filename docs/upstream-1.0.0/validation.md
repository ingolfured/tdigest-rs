# Historical validation record, 6 November 2026

These checks ran on a dual engine build derived from `0c94d899cfd2a63d19ab158084cc38dc1273a575`. The numerical parity and performance results below describe that build. See the [migration guide](../../ROLLOUT.md) for the current shared core behavior.

## Completed local checks

| Check | Result |
| --- | --- |
| `make build` | Rust/CLI, Python extension and Java/JNI JAR built as 1.0.0 |
| `make test`: Rust | 160 passed; three optional diagnostics skipped |
| `make test`: Python/coherence/fast quality | 658 passed; zero failures, errors or skips in JUnit |
| Original upstream Python suite | **91 passed**, zero failures/errors/skips/xfails; separately reported |
| Java and bootstrap | 20 JUnit tests and nine bootstrap tests passed |
| Installed interface runner | 91 original + 117 added compatibility + 236 modern/identity cases passed separately |
| `make quality-regression` | 756 profiles measured: 746 passed, **10 expected failures**; frozen regression gate passed, overall accuracy remains `KNOWN_LIMITS` |
| `make python-support-test` | One wheel built from source passed 50 configurations with Polars and six without it across Python 3.10 to 3.15 |
| Standalone JAR and `verifyJava11Bytecode` | Passed locally on JDK 21; other JDKs are independent Actions gates |
| Rust format/Clippy; selected Python Ruff format/lint | Passed; existing Clippy warnings remain warnings |
| Original source and test integrity | Pinned bytes/inventory verified; a modified temporary test copy was correctly rejected |
| Published package upgrade | All 91 original tests passed on authentic 0.1.0, after pip upgrade to 1.0.0 and after uninstall/reinstall |
| Genuine published pickle migration | 32 pickles written using protocol 5 from published 0.1.0 preserved the original loader's means, weights and query bits after upgrade and reinstall |

Each of the 50 configurations with Polars ran 91 original, 117 extra compatibility
and 236 tests of the capacity API and package identity. Each of the six configurations with NumPy alone ran
91 original, 117 compatibility and 123 tests of the Python capacity API and package identity, and verified
that Polars was absent. Each configuration also checked dependency metadata, `pip check`, clean
installation and optional extra installation without replacing compatible Polars.
The Polars versions are 1.0.0, 1.20.0, 1.38.1, 1.44.2 and 2.0.0, combined with the
supported NumPy/runtime versions in the executable matrix.

The upgrade check uses CPython 3.12.15 / NumPy 1.26.4 and 32 nonempty states:
Float32/Float64 × sizes 1/2/32/1,000 × two seeds × delta 30/300. Empty construction
is rejected by the published API and remains rejected. Migration expectations
come from loading the genuine old pickle with the old package, preserving its
historical restore behavior. The additional frozen published fixtures remain in
the normal suite. Loading some old NumPy encoded fixtures on newer NumPy emits
NumPy's own namespace deprecation warning; no legacy engine deprecation was
introduced by this release.

## Artifact identity

| Artifact | SHA256 |
| --- | --- |
| Published `tdigest_rs-0.1.0-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | `62ee8d5a01226d020a2ab11a956292c38beab3f34d2d9fa7a8fca22c3e5d4bbf` |
| Candidate `tdigest_rs-1.0.0-cp310-abi3-manylinux_2_28_x86_64.whl` | `704f5f2fce2e2edc16a3f60ff0f4829e096a772f38372a15fc79a2cddf9cc100` |
| Candidate native extension | `c66b943746ef5e2baea3c9dc346af6051941c1f8b9a43a980272719d81e4f6f3` |
| Candidate source archive `tdigest_rs-1.0.0.tar.gz` | `59acdf7aff79cd2c854a3e7347b9733937aabced7c2cbf21beed08e5d82a0bfb` |

The source archive was checked for package/test completeness and original test
bytes, then compiled once using CPython 3.10. The same wheel was installed into
all 56 runtime cells and used for the upgrade and [performance comparison](performance.md).
Later documentation/CI edits produce a different source archive hash. These
local hashes identify the measured artifacts, not future release artifacts.
