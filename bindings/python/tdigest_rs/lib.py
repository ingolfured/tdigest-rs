from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Dict, Type, Union

import numpy as np
import numpy.typing as npt

from ._modern import TDigest as _ModernDigest
from ._shared import DEFAULT_DELTA as DEFAULT_DELTA, _UNSET
from .tdigest_rs import _TDigestInternal32, _TDigestInternal64  # type: ignore


NpFloatArr = npt.NDArray[Union[np.float32, np.float64]]
_TDigestInternal = Union[_TDigestInternal32, _TDigestInternal64]


@dataclass
class TDigest(ABC):
    """Use delta for the original Python calling convention or max_size for the modern digest."""

    from_bytes = staticmethod(_ModernDigest.from_bytes)
    merge_all = staticmethod(_ModernDigest.merge_all)
    _digest: _TDigestInternal

    def merge(self, other: Any, delta: float = DEFAULT_DELTA) -> "TDigest":
        if not isinstance(other, TDigest) or isinstance(other, _ModernDigest):
            raise ValueError(f"Cannot merge object {other} to {self}")

        if (sc := self._digest.__class__) != (oc := other._digest.__class__):
            raise TypeError(f"self ({sc}) has a different type to ({oc})")

        digest = self._digest.merge(other._digest, delta=delta)
        return self.__class__(digest)

    @cached_property
    def means(self) -> NpFloatArr:
        return self._digest.means

    @cached_property
    def weights(self) -> npt.NDArray[np.uint32]:
        return self._digest.weights

    def quantile(self, q: float) -> float:
        return self._digest.quantile(q)

    def cast_precision(self, precision: str) -> TDigest:
        target = {"f32": _TDigestInternal32, "f64": _TDigestInternal64}.get(precision)
        if target is None:
            raise ValueError("precision must be 'f32' or 'f64'")
        return type(self)(self._digest.cast(target))

    def median(self) -> float:
        return self._digest.median()

    def trimmed_mean(self, lower: float, upper: float) -> float:
        return self._digest.trimmed_mean(lower, upper)

    @classmethod
    def from_array(cls, arr=_UNSET, delta=_UNSET, *, max_size=_UNSET, **options):
        if arr is _UNSET:
            arr = options.pop("data", _UNSET)
        if arr is _UNSET:
            raise TypeError("from_array requires observations")
        if max_size is not _UNSET:
            if delta is not _UNSET:
                raise ValueError("specify either max_size or delta")
            return _ModernDigest.from_array(arr, max_size=max_size, **options)
        if options:
            raise TypeError("specify max_size to use modern constructor options")
        internal = cls._get_internal_cls(arr)
        return cls(internal.from_array(arr, DEFAULT_DELTA if delta is _UNSET else delta))

    @classmethod
    def from_means_weights(cls, arr, weights, delta=_UNSET, *, max_size=_UNSET, **options):
        if max_size is not _UNSET:
            if delta is not _UNSET:
                raise ValueError("specify either max_size or delta")
            return _ModernDigest.from_means_weights(arr, weights, max_size=max_size, **options)
        if options:
            raise TypeError("specify max_size to use modern constructor options")
        internal = cls._get_internal_cls(arr)
        return cls(internal.from_means_weights(arr, weights, DEFAULT_DELTA if delta is _UNSET else delta))

    @classmethod
    def from_dict(cls, d):
        if "wire_b64_v3" in d or "max_size" in d or "precision" in d:
            return _ModernDigest.from_dict(d)
        means = np.array(d["means"])
        weights = np.array(d["weights"])
        if means.shape == weights.shape == (0,) and weights.dtype == np.uint32:
            return cls(cls._get_internal_cls(means).empty(DEFAULT_DELTA))
        return cls.from_means_weights(arr=means, weights=weights)

    def to_dict(self) -> Dict[str, Any]:
        return {"means": self.means, "weights": self.weights}

    def __len__(self) -> int:
        return len(self._digest)

    def __getstate__(self) -> object:
        return self.to_dict()

    def __setstate__(self, d: Dict[str, Any]) -> None:
        obj = self.__class__.from_dict(d)
        self._digest = obj._digest
        self.__dict__.pop("means", None)
        self.__dict__.pop("weights", None)

    def __copy__(self) -> "TDigest":
        means = self.means.copy()
        weights = self.weights.copy()
        return self.__class__.from_dict({"means": means, "weights": weights})

    def __deepcopy__(self, memo: Any) -> "TDigest":
        return self.__copy__()

    @staticmethod
    def _get_internal_cls(arr: NpFloatArr) -> Type[_TDigestInternal]:
        match arr.dtype:
            case np.float32:
                return _TDigestInternal32
            case np.float64:
                return _TDigestInternal64
            case _:
                raise TypeError(f"TDigest is not implemented for arr with type {arr.dtype}")

    def update(
        self, buffer: NpFloatArr, delta: float = DEFAULT_DELTA, merge_delta: float = DEFAULT_DELTA
    ) -> "TDigest":
        buffer_digest = TDigest.from_array(buffer, delta)
        return self.merge(buffer_digest, merge_delta)


TDigest.register(_ModernDigest)
