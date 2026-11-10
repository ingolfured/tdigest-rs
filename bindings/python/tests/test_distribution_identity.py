"""The upstream distribution owns version reporting for both public APIs."""

from importlib.metadata import version
import subprocess
import sys

from packaging.version import Version


def test_public_versions_match_distribution_and_native():
    import tdigest_rs
    import tdigest_rs._native as native

    from importlib.util import find_spec

    assert find_spec("gr_tdigest") is None
    expected = version("tdigest-rs")
    assert tdigest_rs.__version__ == expected
    assert Version(native.__version__) == Version(expected)


def test_unrelated_private_distribution_cannot_supply_public_version():
    code = """
import importlib.metadata as metadata
original = metadata.version
expected = original('tdigest-rs')
def lookup(name):
    if name == 'gr-tdigest':
        return '999.0.0'
    return original(name)
metadata.version = lookup
import tdigest_rs
assert tdigest_rs.__version__ == expected
"""
    subprocess.run([sys.executable, "-I", "-c", code], check=True)


def test_original_api_remains_available_without_deprecation_warnings():
    code = """
import numpy as np
from tdigest_rs import TDigest
assert TDigest.__module__ == 'tdigest_rs.lib'
d = TDigest.from_array(np.array([0., 1., 2., 3.]))
d.merge(d).median()
d.update(np.array([4., 5.])).quantile(0.5)
TDigest.from_dict(d.to_dict()).median()
delta32 = TDigest.from_array(np.array([1., 2.], dtype=np.float32), delta=300)
assert delta32.means.dtype == np.float32
assert delta32.cast_precision("f64").merge(d).means.dtype == np.float64
capacity = TDigest.from_array(np.array([1, 2], dtype=np.float16), max_size=64)
assert isinstance(capacity, TDigest)
assert TDigest.from_dict(capacity.to_dict()).to_bytes() == capacity.to_bytes()
assert TDigest.from_bytes(capacity.to_bytes()).inner_kind() == "f64"
assert capacity.merge(capacity) is capacity
assert capacity.count == 4
empty = TDigest.from_array(np.array([np.nan], dtype=np.float32))
import pickle
assert len(pickle.loads(pickle.dumps(empty))) == 0
"""
    subprocess.run([sys.executable, "-I", "-W", "error::DeprecationWarning", "-c", code], check=True)
