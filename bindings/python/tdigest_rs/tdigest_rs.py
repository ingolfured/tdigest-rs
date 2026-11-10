"""Delta-based Python adapter over the shared Rust digest."""

from __future__ import annotations

import math
from typing import Literal, TypeVar
from numpy.typing import NDArray

import numpy as np

from ._modern import TDigest as _ModernDigest


_D = TypeVar("_D", bound="_DeltaDigest")


class _DeltaDigest:
    dtype: type[np.float32] | type[np.float64]
    precision: Literal["f32", "f64"]

    def __init__(self, finite: _ModernDigest, negative: int, positive: int) -> None:
        self._finite = finite
        self._negative = negative
        self._positive = positive
        if finite.count + negative + positive > np.iinfo(np.uint32).max:
            raise ValueError("tdigest: uint32 total weight overflow")

    @classmethod
    def from_array(cls: type[_D], arr: NDArray, delta: float) -> _D:
        return cls._build(arr, None, delta)

    @classmethod
    def from_means_weights(cls: type[_D], arr: NDArray, weights: NDArray[np.uint32], delta: float) -> _D:
        if not isinstance(weights, np.ndarray) or weights.dtype != np.uint32 or weights.ndim != 1:
            raise TypeError("weights must be a one-dimensional uint32 array")
        if arr.shape != weights.shape:
            raise ValueError("means and weights must have the same shape")
        return cls._build(arr, weights, delta)

    @classmethod
    def _build(cls: type[_D], arr: NDArray, weights: NDArray[np.uint32] | None, delta: float) -> _D:
        if not isinstance(arr, np.ndarray) or arr.dtype != cls.dtype or arr.ndim != 1:
            raise TypeError(f"expected a one-dimensional {cls.dtype.__name__} array")
        if not arr.size:
            raise ValueError("Array must be non-empty!")
        finite = np.isfinite(arr)
        negative = positive = 0
        if not finite.all():
            neg, pos = np.isneginf(arr), np.isposinf(arr)
            negative = int(neg.sum() if weights is None else weights[neg].sum())
            positive = int(pos.sum() if weights is None else weights[pos].sum())
            arr = arr[finite]
            if weights is not None:
                weights = weights[finite]
        if weights is None:
            digest = _ModernDigest.from_array(arr, delta=delta, precision=cls.precision)
        else:
            keep = weights > 0
            digest = _ModernDigest.from_means_weights(arr[keep], weights[keep], delta=delta, precision=cls.precision)
        return cls(digest, negative, positive)

    def __len__(self) -> int:
        return len(self._finite) + bool(self._negative) + bool(self._positive)

    @property
    def means(self) -> NDArray:
        finite = self._finite.means.astype(self.dtype, copy=False)
        if self._negative or self._positive:
            return np.concatenate(
                ([-np.inf] if self._negative else [], finite, [np.inf] if self._positive else [])
            ).astype(self.dtype)
        return finite

    @property
    def weights(self) -> NDArray[np.uint32]:
        finite = self._finite.weights
        if self._negative or self._positive:
            finite = np.concatenate(
                ([self._negative] if self._negative else [], finite, [self._positive] if self._positive else [])
            )
        return finite.astype(np.uint32)

    def merge(self: _D, other: _D, delta: float) -> _D:
        if type(self) is not type(other):
            raise TypeError("cannot merge digests with different mean precision")
        if self._finite.delta == other._finite.delta == delta:
            finite = _ModernDigest.merge_all([self._finite, other._finite])
        else:
            means = np.concatenate((self._finite.means, other._finite.means))
            weights = np.concatenate((self._finite.weights, other._finite.weights))
            finite = _ModernDigest.from_means_weights(means, weights, delta=delta, precision=self.precision)
        return type(self)(finite, self._negative + other._negative, self._positive + other._positive)

    def quantile(self, q: float) -> float:
        if not self._negative and not self._positive:
            return self._finite.quantile(q)
        if not 0 <= q <= 1:
            raise ValueError("quantile must be in [0, 1]")
        count = self._finite.count
        rank = q * (self._negative + count + self._positive)
        if self._negative and rank <= self._negative:
            return -math.inf
        if self._positive and rank >= self._negative + count:
            return math.inf
        return self._finite.quantile((rank - self._negative) / count)

    def median(self) -> float:
        return self.quantile(0.5)

    def trimmed_mean(self, lower: float, upper: float) -> float:
        if not self._negative and not self._positive:
            return self._finite.trimmed_mean(lower, upper)
        if not 0 <= lower <= upper <= 1:
            raise ValueError("trimmed_mean bounds must satisfy 0 <= lower <= upper <= 1")
        if lower == upper:
            return self.quantile(lower)
        count = self._finite.count
        total = self._negative + count + self._positive
        lo, hi = lower * total - self._negative, upper * total - self._negative
        if lo < 0 and hi > count:
            return math.nan
        if lo < 0:
            return -math.inf
        if hi > count:
            return math.inf
        return self._finite.trimmed_mean(lo / count, hi / count)

    def cast(self, target: type[_D]) -> _D:
        return target(self._finite.cast_precision(target.precision), self._negative, self._positive)

    @classmethod
    def empty(cls: type[_D], delta: float) -> _D:
        return cls(_ModernDigest.from_array([], delta=delta, precision=cls.precision), 0, 0)

    def n_zero_weights(self) -> int:
        return 0


class _TDigestInternal32(_DeltaDigest):
    dtype = np.float32
    precision = "f32"


class _TDigestInternal64(_DeltaDigest):
    dtype = np.float64
    precision = "f64"
