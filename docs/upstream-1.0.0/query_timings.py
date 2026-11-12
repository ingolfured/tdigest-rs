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


def capacity_queries(seed):
    rng = np.random.RandomState(seed)
    values = rng.permutation(np.arange(1_000_000, dtype=np.float64))
    digest = TDigest.from_array(values, max_size=146, precision="f64")
    assert len(digest.means) == 146
    assert digest.median() == 499_999.5 and digest.quantile(0.99) == 989_999.5
    context = {"digest": digest}
    return {
        "max_size": 146,
        "centroids": len(digest.means),
        "median": measure("digest.median()", context, 200_000),
        "p99": measure("digest.quantile(0.99)", context, 200_000),
    }


def polars_query(seed):
    import polars as pl
    import tdigest_rs as td

    groups, rows = 256, 4096
    values = np.random.RandomState(seed).permutation(np.arange(groups * rows))
    frame = pl.DataFrame({"group": values // rows, "value": values.astype(np.float64)})
    states = frame.group_by("group").agg(td.tdigest("value", max_size=200).alias("digest"))
    counts = states.select(pl.col("digest").struct.field("centroids").list.len()).to_series()
    assert counts.min() == counts.max() == 200
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
        "centroids_per_group": int(counts.min()),
        "polars": pl.__version__,
        "threads": pl.thread_pool_size(),
        "both_queries": measure("query.collect()", {"query": query}, 25),
    }


def cdf_queries(seed):
    import polars as pl
    import tdigest_rs as td

    rng = np.random.default_rng(seed)
    training = pl.DataFrame({"x": rng.normal(size=40_000)})
    state = training.select(td.tdigest("x", max_size=200).alias("digest"))
    digest = TDigest.from_bytes(state.select(td.to_bytes("digest")).item())
    assert len(digest.means) == 200
    probes = rng.normal(size=65_536)
    query = pl.DataFrame({"x": probes}).lazy().select(td.cdf(pl.lit(state["digest"]), pl.col("x")))
    np.testing.assert_array_equal(query.collect().to_series().to_numpy(), digest.cdf(probes))
    result = {
        "threads": pl.thread_pool_size(),
        "polars": pl.__version__,
        "centroids": 200,
        "polars_cdf": measure("query.collect()", {"query": query}, 18),
    }
    if pl.thread_pool_size() == 1:
        result["numpy_cdf"] = measure("digest.cdf(probes)", {"digest": digest, "probes": probes}, 18)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("api", choices=("python", "capacity", "polars", "cdf"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = {"python": python_calls, "capacity": capacity_queries, "polars": polars_query, "cdf": cdf_queries}[
        args.api
    ](args.seed)
    print(json.dumps({"version": version("tdigest-rs"), "api": args.api, "seed": args.seed, **result}))
