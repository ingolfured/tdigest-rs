"""Time public queries on prebuilt digests. Build time is excluded."""

import argparse
import hashlib
from importlib.metadata import version
import json
from statistics import median
from timeit import Timer

import numpy as np
from tdigest_rs import TDigest


def measure(statement, context, iterations):
    timer = Timer(statement, globals=context)
    timer.timeit(max(1, iterations // 10))
    samples = [1e9 * elapsed / iterations for elapsed in timer.repeat(repeat=7, number=iterations)]
    return {"ns_per_call": samples, "median_ns": median(samples)}


def state(digest):
    checksum = hashlib.sha256(digest.means.tobytes() + digest.weights.tobytes()).hexdigest()
    return {"centroids": len(digest), "sha256": checksum}


def python_calls(seed):
    rng = np.random.RandomState(seed)
    n = 1_000_000
    left = TDigest.from_array(rng.permutation(np.arange(n, dtype=np.float64)), delta=300)
    right = TDigest.from_array(rng.permutation(np.arange(n, 2 * n, dtype=np.float64)), delta=300)
    context = {"left": left, "right": right}
    assert left.median() == 499_999.5 and left.quantile(0.99) == 989_999.5
    merged = left.merge(right)
    assert merged.weights.sum() == 2 * n
    return {
        "states": [state(digest) for digest in (left, right, merged)],
        "median": measure("left.median()", context, 200_000),
        "p99": measure("left.quantile(0.99)", context, 200_000),
        "merge": measure("left.merge(right)", context, 3_000),
    }


def polars_query(seed):
    import polars as pl
    import tdigest_rs as td

    groups, rows = 256, 4096
    values = np.random.RandomState(seed).permutation(np.arange(groups * rows))
    frame = pl.DataFrame({"group": values // rows, "value": values.astype(np.float64)})
    states = frame.group_by("group").agg(td.tdigest("value", max_size=200).alias("digest"))
    query = (
        states.lazy()
        .group_by("group")
        .agg(
            td.median("digest").alias("median"),
            td.quantile("digest", 0.99).alias("p99"),
        )
    )
    result = query.collect().sort("group")
    assert result.height == groups
    for group, p50, p99 in result.iter_rows():
        group_values = np.arange(group * rows, (group + 1) * rows, dtype=np.float64)
        reference = TDigest.from_array(group_values, max_size=200)
        assert (p50, p99) == (reference.median(), reference.quantile(0.99))
    return {
        "groups": groups,
        "polars": pl.__version__,
        "threads": pl.thread_pool_size(),
        "both_queries": measure("query.collect()", {"query": query}, 25),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("api", choices=("python", "polars"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = python_calls(args.seed) if args.api == "python" else polars_query(args.seed)
    print(json.dumps({"version": version("tdigest-rs"), "seed": args.seed, **result}))
