"""The upstream distribution owns version reporting for both public APIs."""

from importlib.metadata import version
import subprocess
import sys

from packaging.version import Version


def test_public_versions_match_distribution_and_native():
    import gr_tdigest
    import gr_tdigest._gr_tdigest as native
    import tdigest_rs

    expected = version("tdigest-rs")
    assert tdigest_rs.__version__ == gr_tdigest.__version__ == expected
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
import gr_tdigest
import tdigest_rs
assert gr_tdigest.__version__ == tdigest_rs.__version__ == expected
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
"""
    subprocess.run([sys.executable, "-I", "-W", "error::DeprecationWarning", "-c", code], check=True)
