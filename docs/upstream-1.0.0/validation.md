# Historical validation record, 6 November 2026

These checks ran on a two-engine build derived from `0c94d899cfd2a63d19ab158084cc38dc1273a575`. The numerical parity and performance results below describe that build. See the [migration guide](../../ROLLOUT.md) for the current single-engine behavior.

## Completed local checks

| Check | Result |
| --- | --- |
| `make build` | Rust/CLI, Python extension and Java/JNI JAR built as 1.0.0 |
| `make test`: Rust | 160 passed; three pre-existing slow diagnostic/proof tests ignored, not counted as passes |
| `make test`: Python/coherence/fast quality | 658 passed; zero failures, errors or skips in JUnit |
| Original upstream Python suite | **91 passed**, zero failures/errors/skips/xfails; separately reported |
| Java and bootstrap | 20 JUnit tests and nine bootstrap tests passed |
| Installed-interface runner | 91 original + 117 added compatibility + 236 modern/identity cases passed separately |
| `make quality-regression` | 756 profiles measured: 746 passed, **10 expected failures**; frozen regression gate passed, overall accuracy remains `KNOWN_LIMITS` |
| `make python-support-test` | One source-built wheel passed 50 Polars-enabled cells and six Polars-free cells across Python 3.10–3.15 |
| Standalone JAR and `verifyJava11Bytecode` | Passed locally on JDK 21; other JDKs are independent Actions gates |
| Rust format/Clippy; selected Python Ruff format/lint | Passed; existing Clippy warnings remain warnings |
| Original-source/test integrity | Pinned bytes/inventory verified; a modified temporary test copy was correctly rejected |
| Published-package upgrade | Original 91-case suite passed on authentic 0.1.0, after pip upgrade to 1.0.0 and after uninstall/reinstall |
| Genuine published pickle migration | 32 protocol-5 states from published 0.1.0 preserved the original loader's means, weights and query bits after upgrade and reinstall |

Each of the 50 full runtime cells requires 91 original, 117 extra compatibility
and 236 modern/package-identity cases. Each of the six NumPy-only cells requires
91 original, 117 compatibility and 123 modern Python/identity cases, and verifies
that Polars is absent. Cells also check dependency metadata, `pip check`, clean
installation and optional-extra installation without replacing compatible Polars.
The Polars versions are 1.0.0, 1.20.0, 1.38.1, 1.44.2 and 2.0.0, combined with the
supported NumPy/runtime versions in the executable matrix.

The upgrade check uses CPython 3.12.15 / NumPy 1.26.4 and 32 nonempty states:
Float32/Float64 × sizes 1/2/32/1,000 × two seeds × delta 30/300. Empty construction
is rejected by the published API and remains rejected. Migration expectations
come from loading the genuine old pickle with the old package, preserving its
historical restore behavior. The additional frozen published fixtures remain in
the normal suite. Loading some old NumPy-encoded fixtures on newer NumPy emits
NumPy's own namespace deprecation warning; no legacy-engine deprecation was
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

## Required CI and external blockers

The retained upstream workflow covers Rust tests on Linux, Windows and both Mac
architectures; Python interface tests across those platforms; seven wheel targets;
the installed-wheel runtime/upgrade matrix; and the full project/quality gate.
Java 11/17/25 jobs supplement the JDK 21 full-project job. The project jobs also
check standalone native loading and Java 11 bytecode. Results and separate
legacy/compatibility XML/logs are retained as Actions artifacts.

At preparation time, upstream's `CI` workflow is `disabled_inactivity`, and the
connected account has only read access to G-Research's repository. A maintainer
must re-enable/run it and complete the existing upstream approval and app-backed
required check. Fork CI cannot satisfy those upstream controls. No gate has been
disabled or replaced to obtain a pass. The PR was draft when these checks ran. Jenkins is not used.

The 10 statistical limits and three ignored Rust diagnostics remain explicit.
Neither the local checks nor fork CI constitute release approval, publication,
cross-platform performance proof or evidence that every accuracy target passes.
