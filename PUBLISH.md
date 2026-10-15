# Upstream release process

This candidate retains G-Research/tdigest-rs's existing release workflow graph,
SHA-pinned actions, required checks, trusted PyPI publisher and platform matrix.
It does not adopt the private project's crates.io or Maven publishing workflows.

The `create-release.yml` workflow is a maintainer action in the `create-release`
environment. Its version update selects the modern root package `tdigest-rs`
explicitly; it does not bump the preserved `tdigest_core` package or testdata.
The former `bindings/python/Cargo.toml` no longer exists and is not staged.
Root version `2.0.0` is provisional until maintainers choose a release version.

After required CI checks pass for an upstream version tag, `release.yml`
downloads the `python-package-*` artifacts, publishes through the **`release`**
environment's PyPI trusted publisher, and attaches those files to the GitHub
release. Existing action SHA pins and permission boundaries remain in place.
The new source archive joins the platform wheels under that artifact pattern;
the separate runtime evidence artifact is not a package upload.

The Linux runtime job downloads the actual `python-package-x86_64-unknown-linux-gnu`
wheel produced by the platform build matrix and tests that artifact with
`--wheel`; it does not compile a replacement wheel. Its checked source archive
is created separately from `bindings/python`, with Cargo.lock unchanged, then
passed through the same gate using `--sdist`. The runtime evidence records both
artifact hashes, installed native hashes, dependency checks and seven-cell logs.
The other six platform wheel artifacts are still build outputs: source-based
platform tests do not establish installation of those exact repaired/cross-built
wheels. Normalized-sdist rebuild remains a separate release validation step.

Before a release, verify the exact adapted artifacts, including the original
Python and Rust contracts, real same-distribution upgrade/uninstall/reinstall,
the seven-cell NumPy/Polars support gate, normalized-sdist rebuild, and upstream
platform checks. A local `linux_x86_64` wheel is not proof of manylinux or musl
portability. Inspect the repaired tags and actual target requirements.

No safe co-installation with private `gr-tdigest` is claimed: both distributions
own the same two Python namespaces. The default upgrade path assumes the
private distribution is absent. A separate namespace/ownership decision is
needed before supporting environments containing both.

Local `make release-*` targets build artifacts for review. Local `make publish*`
targets intentionally stop with a reference to this document; they do not
publish to PyPI, crates.io or Maven. No credentials, release, tag or upload are
required for the review workflow. Registry release of either Rust package and
Java publication require a separate maintainer decision.
