# Original compatibility suite

The copied tests in `compat/tdigest-rs-upstream/bindings/python/tests` are the
unchanged 91-case upstream Python suite. Their hashes and source pin are in
`compat/tdigest-rs-upstream/PROVENANCE.md`.

They import the production `tdigest_rs` package. There is no test-only module
shadowing the installed implementation. The production wrapper preserves the
original API and delegates to the preserved original numerical core; the modern
API is exposed separately through `gr_tdigest`.

Run `make legacy-strict-test` after building, or `make legacy-wheel-test` to test
the actual release Linux wheel outside the checkout. The wheel gate also runs
exact-output, API, optional-import and published-pickle regressions. The original
suite remains part of `make test`.

Do not edit copied upstream tests or the benchmark to make the replacement pass.
New regressions and provenance belong outside the copied tree. The historical
benchmark is a separate manual tool and is not a release performance claim.

See [the refresh guide](review-refresh.md) for saved-state, Rust API, runtime and
package-ownership boundaries.
