"""Read real published tdigest-rs 0.1.0 pickles through the shared Rust engine."""

import base64
import hashlib
import json
from pathlib import Path
import pickle
import io

import numpy as np
from tdigest_rs._modern import TDigest as Modern

import pytest


FIXTURE = json.loads((Path(__file__).parent / "data" / "published_0_1_0_pickle_golden.json").read_text())


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: case["id"])
def test_published_0_1_0_pickle_migrates_weighted_observations(case):
    # Only unpickle the checked-in, hash-verified synthetic release fixtures.
    payload = base64.b64decode(case["pickle_base64"], validate=True)
    assert hashlib.sha256(payload).hexdigest() == case["pickle_sha256"]
    digest = pickle.loads(payload)
    state = case["expected_old_restored"]
    assert type(digest).__module__ == state["class_module"]
    assert type(digest).__qualname__ == state["class_name"]
    assert digest.means.dtype.str == state["means_dtype"]
    assert digest.weights.dtype.str == state["weights_dtype"]
    old_weights = np.frombuffer(bytes.fromhex(state["weights_hex"]), dtype=state["weights_dtype"])
    assert digest.weights.sum() == old_weights.sum()

    # The pickled state is the pre-restoration set of centroids. Use exactly
    # those observations to derive the expected queries on the new engine.
    class Capture:
        pass

    class StateReader(pickle.Unpickler):
        def find_class(self, module, name):
            if (module, name) == ("tdigest_rs.lib", "TDigest"):
                return Capture
            return super().find_class(module, name)

    saved = StateReader(io.BytesIO(payload)).load()
    expected = Modern.from_means_weights(
        saved.means, saved.weights, delta=300, precision="f32" if saved.means.dtype == np.float32 else "f64"
    )
    np.testing.assert_array_equal(digest.means, expected.means)
    np.testing.assert_array_equal(digest.weights, expected.weights)
    for q in (0, 0.01, 0.5, 0.99, 1):
        assert digest.quantile(q) == expected.quantile(q)
