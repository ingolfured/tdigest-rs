"""Score an installed wheel on the nine recorded columns used in the quality suite."""

import argparse
import csv
from pathlib import Path
import statistics
import sys

import numpy as np
from tdigest_rs import TDigest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/quality"))
from measurements import Q, Exact, build, datasets  # noqa: E402


def delta_digest(values, route):
    if route == "bulk":
        return TDigest.from_array(values, delta=300)
    parts = [TDigest.from_array(chunk, delta=300) for chunk in np.array_split(values, 40)]
    if route == "left40":
        result = parts[0]
        for other in parts[1:]:
            result = result.merge(other, delta=300)
        return result
    while len(parts) > 1:
        parts = [
            parts[i].merge(parts[i + 1], delta=300) if i + 1 < len(parts) else parts[i] for i in range(0, len(parts), 2)
        ]
    return parts[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("delta", "capacity"))
    args = parser.parse_args()
    writer = csv.writer(sys.stdout)
    writer.writerow(
        ["column", "precision", "order", "route", "centroids", "mean_rank_error", "tail_rank_error", "mean_value_error"]
    )
    for column, kind, observations in datasets(ROOT / "tests/quality/data", "extended"):
        if kind != "real":
            continue
        for precision, dtype in (("f32", np.float32), ("f64", np.float64)):
            values = np.array(observations, dtype=dtype)
            exact = Exact(values.tolist())
            for order, data in (("forward", values), ("reverse", values[::-1].copy())):
                for route in ("bulk", "left40", "balanced40"):
                    digest = delta_digest(data, route) if args.mode == "delta" else build(data, precision, 1000, route)
                    estimates = [digest.quantile(q) for q in Q]
                    errors = [exact.rank_error(q, x) for q, x in zip(Q, estimates)]
                    tail = max(e for q, e in zip(Q, errors) if q <= 0.01 or q >= 0.99)
                    value_error = statistics.mean(abs(exact.quantile(q) - x) for q, x in zip(Q, estimates))
                    writer.writerow(
                        [column, precision, order, route, len(digest), statistics.mean(errors), tail, value_error]
                    )


if __name__ == "__main__":
    main()
