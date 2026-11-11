# Publishing tdigest-rs

The proposed upstream release version is `1.0.0`. The root `Cargo.toml` supplies
that version to the Python distribution and JVM artifact. See [the migration guide](ROLLOUT.md).

## Release prerequisites

Run `make build`, `make test` and `make python-support-test` on the final upstream
commit. Review this repository's Rust and Python platform jobs, wheel builds,
tests of installed wheels and interoperability checks. Review the
accuracy limits linked from the README; passing regression checks does not imply
that every statistical accuracy target passes.

Move the pending changelog entries into a versioned section before release.
Merge the approved contribution into G-Research's `main`.

## Existing upstream release workflow

Use the **Create release** workflow (`.github/workflows/create-release.yml`) with
the approved semantic version. It retains the existing `create-release`
environment and GitHub App credentials. It updates the root `tdigest-rs` Cargo
package and lockfile when the version changes, then pushes the corresponding `v*` tag.

The tag triggers **CI**. After the required Rust, Python and interoperability jobs
succeed, the existing release workflow downloads the `python-package-*`
artifacts, publishes the `tdigest-rs` distribution using the `release` environment
and PyPI trusted publishing, and creates the GitHub release. The seven platform
wheel build matrix and pinned action references remain part of that pipeline.
The Linux runtime support job also supplies the checked source distribution.

The original `check-required.yml` workflow and its GitHub App required check stay
in place. Fork CI does not replace the upstream approving review or required check.

## Optional Rust and Maven publication

The upstream automated release publishes Python and GitHub artifacts. Rust and
Maven publication remain separate, explicit maintainer actions. The local Makefile
provides `publish-cargo` and `publish-maven`, but they are not invoked by upstream
CI.

The JVM coordinates are `com.gresearch.tdigest:tdigest-rs`. Set `TDIGEST_SOURCE_SHA`
when building a release JAR to record the source commit alongside the native
payload hash. Configure the Maven destination and credentials only when choosing
to publish that artifact.
