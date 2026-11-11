# Published package pickle migration

These 32 fixtures come from the actual PyPI `tdigest-rs` **0.1.0** Linux wheel,
installed with Python 3.12.12 and NumPy 1.26.4. They cover f32/f64, weighted data,
large uint32 weights, distinct construction/merge deltas, and pickle protocols 4/5.
The generator verifies the wheel SHA256 and checks that the installed wrapper and
native extension are identical to its members. Inputs are synthetic.

The source revision used for the upstream test suite identifies itself as 0.2.0.
The pickle fixtures come from the published 0.1.0 wheel. [PROVENANCE.json](PROVENANCE.json)
records the wheel, generator and fixture hashes.

## Loading a published pickle

The saved fields are centroid means and uint32 weights. Loading reconstructs a
digest from those weighted observations using the default delta of 300. The
migration test compares the reconstructed state and quantiles with the shared
core and checks that the original precision and total mass survive. Earlier
query values are retained in the fixture as historical measurements.

For example, in one Float64 fixture created with delta 5000, even the original
loader compressed 1833 saved centroids to 134. Applications that need to
reproduce a previous calculation should retain the original inputs and version.

Pickles can also depend on the NumPy version. In the recorded rollback test,
NumPy 1.26.4 could not load protocol 5 pickles referring to
`numpy._core.numeric` written by NumPy 2.

## Reproduce and review

Download the original wheel linked in `PROVENANCE.json` and set `WHEEL` to its
local path. In an isolated Linux environment, generate only with the genuine old
package; never regenerate expected outputs from the replacement to accept a drift.

```sh
uv venv --python 3.12 /tmp/tdigest-pickle-original
uv pip install --python /tmp/tdigest-pickle-original/bin/python \
  --only-binary :all: numpy==1.26.4 "$WHEEL"
/tmp/tdigest-pickle-original/bin/python -I compat/published-pickle/generate.py \
  --wheel "$WHEEL" \
  --output bindings/python/tests/data/published_0_1_0_pickle_golden.json
```

The 32 migration cases run in `make test`. The `make legacy-wheel-test`
target also runs them outside the checkout against the installed release wheel,
alongside the 91 original tests and additional compatibility checks. The fixtures
contain the original pickles, so those tests can run without the original wheel.
