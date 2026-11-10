from typing import Literal

from ._modern import TDigest as TDigest

__version__: str

def wire_precision_py(b: bytes) -> Literal["f32", "f64"]: ...
