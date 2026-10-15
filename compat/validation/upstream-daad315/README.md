# Actual upstream Linux validation

Candidate `daad31585d8d88cbffeeeba206ccfeebd733e9a1` builds distribution `tdigest-rs` version 2.0.0 with the
original `tdigest_rs` default API and opt-in `gr_tdigest`. This result belongs to
that adapted source and its actual artifacts, not private `ff73cfa` or the earlier
name-only prototype. The Java namespace remains `com.gresearch.tdigest`.

Canonical Linux/WSL build, test and lint pass: 336 Python/coherence
cases plus 91 unchanged original cases, 121 Rust tests and Java.
Three pre-existing Rust tests remain ignored. Each of the direct optimized wheel
and its independently source-rebuilt wheel passes 2,036 installed test instances:
six CPython 3.10-3.12 / NumPy 1-2 cells each run 208 compatibility + 92 modern cases;
the Polars-free cell runs 208 + 28. No installed cases are skipped or xfailed.

The actual direct wheel upgrades the authentic published 0.1.0 distribution,
removes its native module, survives uninstall/reinstall, and preserves 32 exact
old-restored states. All 208 compatibility cases pass after upgrade and reinstall.
This uses an explicit NumPy 1.26.4 to 2.3.4 dependency transition, with normal pip
dependency checks. It does not prove unconstrained resolver or co-installation
behavior. The private gr-tdigest distribution was absent.

The preserved first lifecycle attempt stopped during scratch-runner preparation:
it incorrectly counted the snapshot's separate benchmark as a seventh suite file.
No environment or installation had begun; this was not a package or test failure.
The reviewed v2 runner verifies the exact six test/support files and all seven
snapshot checksums against original Git objects. The passing lifecycle uses v2;
failed-v1-invocation.json retains the earlier failure and original runner hashes.

Unchanged numerical probes from private ff73cfa pass against this upstream native:
800 weighted-point digests and 1,440 compressed routes / 3,840 states. These are
bounded invariant checks, not a new speed or held-out accuracy comparison.

Source, wheel/native/archive identities and counts are in validation.json;
source-files.json identifies each preserved report/log. Binary wheels, installed
environments and extracted rebuild trees are retained locally, not bundled here.
Historical private performance/accuracy results retain their original labels.
They remain in the separate private repository: [validation history](https://github.com/ingolfured/gr-tdigest/blob/4bb78de91f7214cb811a35b3ed4bdcb7b2fe4685/compat/validation/README.md),
[timing evidence](https://github.com/ingolfured/gr-tdigest/blob/4bb78de91f7214cb811a35b3ed4bdcb7b2fe4685/compat/performance/README.md) and
[held-out accuracy](https://github.com/ingolfured/gr-tdigest/blob/4bb78de91f7214cb811a35b3ed4bdcb7b2fe4685/compat/accuracy/held-out-20261015/README.md).

Local Linux results do not certify manylinux minimum-glibc deployment, musllinux,
macOS, Windows or installation of every configured release artifact. Original
Rust root-path consumers must select src/upstream. Provisional version 2.0.0,
registry ownership, independent namespace ownership and release remain decisions.
Old pickle reconstruction at default delta 300 and NumPy 2 protocol 5 rollback limits
remain inherited/disclosed. No original-to-modern numerical switch is implicit.
