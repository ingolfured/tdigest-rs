# Upgrading to `tdigest-rs` 1.0

We wanted to build one digest per service in Polars, find the percentile rank of every request, and let a Java service or a Python notebook query the same summary later. We also needed to know how much space those summaries would take as traffic grew. Polars, Python and Java now share the Rust code that builds and queries them.

## Choose the Python API with `delta=` or `max_size=`

Both APIs use `from tdigest_rs import TDigest`. When you call `from_array` or `from_means_weights`, the sizing argument selects how the digest behaves.

| If you want | Example | Behaviour |
| --- | --- | --- |
| **The original 0.1.0 Python API** | `TDigest.from_array(values, delta=300)` | Omitting the sizing argument also selects `delta=300`. Your existing calls and pickles work. `merge` returns a new digest. |
| **The new 1.0 Python API** | `TDigest.from_array(values, max_size=200)` | Choose a centroid limit, query percentile ranks with `cdf` and save bytes for other languages. `merge` updates the digest in place. |

Choose one sizing argument. Passing both raises `ValueError`. Both APIs use the 1.0 Rust engine, so keeping `delta=` preserves the original calling behaviour while some numerical estimates change. [Two quantiles that change](#two-quantiles-that-change)

All 91 original Python tests passed unchanged before and after we installed 1.0 over the published 0.1.0 wheel on Linux. The upgrade test also opened 32 pickles written by 0.1.0 and checked that each retained its total weight. Version 1.0 supports CPython 3.10 through 3.15. Polars is optional. [Upgrade test](scripts/test_package_upgrade.py)

## What you gain over 0.1.0

* **Percentile ranks in Polars.** The original Python API could tell you the latency at the 99th percentile. The new cumulative distribution function (CDF) answers the reverse question for a whole column in a lazy Polars query. Timing the rank lookup alone, Polars ranked 65,536 values against one digest in 1.699 ms on one CPU and 0.363 ms on eight. NumPy took 2.686 ms on one CPU. These are medians across six runs.
* **A fixed centroid budget per group.** Set `max_size=200` and the default policy keeps at most 200 centroids per digest after builds and merges. For 1,000 service groups, that gives you a ceiling of 200,000 centroids regardless of the number of requests. You can also choose among five scale functions to control where the digest keeps more detail.
* **Exact answers for repeated values that stay together.** A centroid records whether all its observations had the same value. If the requested rank falls inside the weight at that value, 1.0 returns it exactly. This matters for counts, rounded timings and other data with ties.
* **Updates to an existing summary.** With `max_size=`, you can add batches of values and counts, give older data less weight before merging it with a new batch, or convert stored latencies from milliseconds to seconds. These operations work on the digest itself. [Python API](README.md#python)
* **The same digest in Python, Rust and on the JVM.** Write a digest from Polars and open its bytes in Java, Kotlin or Scala. A Spark job can pass it between executors. The Rust CLI can build a digest from a CSV and query that same file format from the shell. [CLI example](README.md#rust-and-the-cli) and [JVM examples](bindings/java/README.md)

There are gains with the original settings too. At `delta=300`, average rank error fell in 102 of 108 comparisons on recorded data. The build from one million shuffled values took 30.27 ms in 1.0 and 107.75 ms in 0.1.0, with identical centroids. [Accuracy results](#accuracy-with-the-existing-settings) and [query timings](#median-and-percentile-query-speed)

## One digest for Polars, Python and Java

Was 48 ms slow for search? Was it slow for checkout? We build one digest per service, collect the latencies for each service into a list and join each list to its digest. One call to `td.cdf` then ranks the whole list. The row index puts the results back in request order.

```python
import polars as pl
import tdigest_rs as td

requests = pl.LazyFrame({
    "service": ["search"] * 4 + ["checkout"] * 4,
    "latency_ms": [12.0, 24.0, 48.0, 48.0, 48.0, 48.0, 72.0, 90.0],
})
by_service = (
    requests.group_by("service")
    .agg(td.tdigest("latency_ms", max_size=200).alias("digest"))
    .collect()
)
ranked = (
    requests.with_row_index("row")
    .group_by("service").agg("row", "latency_ms")
    .join(by_service.lazy(), on="service")
    .select(
        "service", "row", "latency_ms",
        td.cdf("digest", pl.col("latency_ms")).alias("percentile_rank"),
    )
    .explode("row", "latency_ms", "percentile_rank")
    .sort("row").drop("row")
)
print(ranked.collect())
```

For search, two requests were faster than 48 ms and two tied. Each tie counts half, so the rank is (2 + 1) / 4, or **75%**. For checkout, the two requests at 48 ms were the fastest. Their rank is (0 + 1) / 4, or **25%**.

For a table of historical digests, use the same pattern with the keys that identify each digest, such as product and day. Polars reads each digest into Rust once for that group. Rust builds the running weights once for the list and uses a binary search for each value. Joining the digest to individual ticks first makes the current plugin copy the centroid data and rebuild the running weights for every tick. [Polars CDF implementation](src/polars_expr.rs) and [Rust rank calculation](src/tdigest/cdf.rs)

### Open the Polars digest in Python or Java

To share the search digest, save the group summary as bytes. Here Python opens the saved file and asks the same question about 48 ms.

```python
from pathlib import Path

search = by_service.filter(pl.col("service") == "search")
saved = Path("search.tdig")
saved.write_bytes(search.select(td.to_bytes("digest")).item())
assert td.TDigest.from_bytes(saved.read_bytes()).cdf(48.0) == 0.75
```

A Java service can open that same file. This prints `0.75` using the same Rust calculation as the Polars expression.

```java
import com.gresearch.tdigest.TDigest;
import java.nio.file.Files;
import java.nio.file.Path;

class SearchRank {
    public static void main(String[] args) throws Exception {
        byte[] data = Files.readAllBytes(Path.of("search.tdig"));
        try (TDigest digest = TDigest.fromBytes(data)) {
            System.out.println(digest.cdf(new double[]{48.0})[0]);
        }
    }
}
```

The default format, TDIG v3, keeps the observed minimum and maximum along with the centroid means, weights, precision and compression settings. Version 1.0 also reads TDIG v1 and v2. The JVM examples exercise the same JAR from Kotlin and Scala and transfer digests through a Spark shuffle, broadcast and checkpoint. [Java setup and examples](bindings/java/README.md)

### How much space does a digest need?

A centroid stores a mean, a weight and whether it represents one distinct value or several. With `max_size=200`, the default policy includes both endpoints in the limit. Here is the space used when all 200 centroids are present.

| Mean precision | Space for 200 centroid records in Rust on Linux x86_64 | Maximum size of the saved TDIG v3 digest |
| --- | ---: | ---: |
| Float32 | 3,200 bytes | 2,664 bytes |
| Float64 | 4,800 bytes | 3,464 bytes |

On the tested build, each Rust record occupies 16 or 24 bytes including padding. For a process memory budget, also allow for the digest object, spare allocation capacity and temporary buffers used while building or merging. The file size is exact for 200 centroids with the default policy. It includes a 64 byte header and 13 or 17 bytes per centroid. [TDIG format](src/tdigest/wire.rs)

With `singleton_policy="edges"`, you can reserve extra centroids at each end. The total bound becomes `max_size + 2 * pin_per_side`. For example, pinning three on each side with `max_size=200` allows up to 206. The original `delta=` setting controls compression and has no fixed centroid count.

### Choosing where the digest keeps more detail

At a given capacity, the scale function determines how the digest distributes centroids between the middle and the extremes. That matters when the slowest 1% of requests are the ones you care about. The five choices with `max_size=` are `QUAD`, `K1`, `K2`, `K2NORM` and `K3`. If you use Ted Dunning's Java library, `K2NORM` corresponds to its `K_2`, and `K2` corresponds to its `K_2_NO_NORM`. [Scale functions](src/tdigest/scale.rs)

## The same Python code runs on both releases

With `delta=`, Float32 and Float64 arrays keep their precision. We ran this example on both releases. It merges two digests, queries the result and restores it from a dictionary.

```python
import numpy as np
from tdigest_rs import TDigest

first = TDigest.from_array(np.array([10, 20, 30], dtype=np.float32), delta=300)
second = TDigest.from_array(np.array([40, 50], dtype=np.float32), delta=300)
combined = first.merge(second)

assert first.weights.sum() == 3
assert combined.weights.sum() == 5
assert combined.median() == 30
assert combined.quantile(0.95) == 50
assert combined.trimmed_mean(0.1, 0.9) == 30
restored = TDigest.from_dict(combined.to_dict())
assert restored.weights.sum() == 5
```

Old pickles store the means and weights of the centroids. Version 1.0 reads those saved values and uses its own calculation for subsequent queries. If a test compares a quantile with an exact number from 0.1.0, check the expected value when upgrading. [Two quantiles that change](#two-quantiles-that-change)

For Rust callers, the upgrade includes an API change. Move from the original `tdigest_core` crate to the root `tdigest-rs` crate and handle errors from checked operations.

## Accuracy with the existing settings

We asked both releases for quantiles on nine columns of bike rental and energy data, using `delta=300` throughout. We checked each answer against the sorted observations. If we ask for the 99th percentile and the answer lands at the 98th, the rank error is one percentage point. Value error measures the difference in the column's own units, such as degrees or bike rentals.

| Measure | Lower error in 1.0 | Same error | Higher error in 1.0 |
| --- | ---: | ---: | ---: |
| Average rank error | 102 | 0 | 6 |
| Worst rank error among the tested percentiles at or below 1% and at or above 99% | 104 | 4 | 0 |
| Average value error | 100 | 0 | 8 |

**When we built each digest in one pass, all 36 comparisons improved on all three measures.** The other 72 comparisons split each column into 40 parts and merged them in sequence or in pairs. We tested both Float32 and Float64 and read each column forwards and backwards.

All six increases in average rank error came from merging the outdoor temperature column. The largest increase in average rank error was **0.00335 percentage points**. In that run 1.0 kept 253 centroids and 0.1.0 kept 268. Applying the old query calculation to the new centroids still gave a higher error, so the way the observations were grouped accounts for at least part of the difference. Across the eight increases in average value error, the largest increases were less than 0.002 degrees for temperature and less than 0.05 of a rental for bike counts. [Centroid counts, errors and results with the old query calculation](docs/upstream-1.0.0/recorded-accuracy.csv)

<details>
<summary>Results at other digest sizes</summary>

With `max_size=1000`, 1.0 had lower average rank error than 0.1.0 at `delta=300` in all 108 comparisons. That setting allows a larger digest. The wider accuracy suite covers 756 cases. Ten synthetic cases at `max_size=32` exceed the rank and CDF targets after repeated merges. An earlier study that matched storage found larger peak value errors on the energy data and several synthetic distributions where the original algorithm did better. [Ten cases outside the targets](tests/quality/known-limits.json) and [equal storage study](https://github.com/ingolfured/tdigest-rs/blob/1292b6110578bb9561a168f0898254a62aaf1fcd/compat/quality-20261020/RESULTS.md)

</details>

### Two quantiles that change

When every observation in a centroid has the same value, the centroid is called **atomic**. It can represent one observation or many repeats. These examples use the default Python settings on both releases.

| Query | 0.1.0 | 1.0 |
| --- | ---: | ---: |
| 10th percentile of `[1, 2]` | about 0.7 | 1.0 |
| Median from means `[0, 10]` and weights `[90, 10]` | 1.0 | 0.0 |

In the first example, 0.1.0 returned a value below the smallest observation. In the second, the median falls inside the 90 observations at zero. Version 1.0 returns zero with the default `delta=300`, which turns edge protection off. Exactly at the boundary between two atomic centroids it returns their midpoint, so the median of `[1, 2]` is still 1.5.

We also checked the middle rank of each of the 100 observations in the weighted example, from 0.5% through 99.5%. Given the two means and their counts, **1.0 returned the observed value at all 100 ranks. The published 0.1.0 returned it at five.** Both releases got every rank right when we supplied all 100 observations individually.

## Median and percentile query speed

With 1.0, Polars computed the median and 99th percentile for **256 prebuilt group digests in 2.18 ms** using eight CPU cores. The same query took 14.48 ms on one core. Polars schedules the groups itself. Version 0.1.0 had no native Polars expressions.

For existing Python callers, we timed the same calls on prebuilt Float64 digests with identical centroids at `delta=300`. Times below are per call, with 0.1.0 first.

* **Queries.** Median was effectively tied (121 ns versus 123 ns). The 99th percentile took 20% less time in 1.0 (154 ns versus 123 ns).
* **Merging two digests.** The merge took 3.27 µs versus 9.27 µs, or **2.83 times as long** in 1.0. Both releases merged the same two sets of 146 centroids into the same 174. [Recorded measurements](docs/upstream-1.0.0/query-timings.jsonl)

### The original Python benchmark

We ran the 0.1.0 benchmark unchanged on both wheels. It builds a digest from each of 5,000 arrays of 16,000 values at `delta=10000`, then merges each digest with itself at the default `delta=300`. The script repeats this ten times using 32 joblib threads. We report the median elapsed time for the builds and merges together across three matching seeds on the same machine. [Original benchmark in 0.1.0](https://github.com/G-Research/tdigest-rs/blob/v0.1.0/bindings/python/benchmarks/run.py)

| Workload | 0.1.0 | 1.0 | Change |
| --- | ---: | ---: | --- |
| Original Python benchmark | 2.521 s | 2.896 s | 1.0 took 14.9% longer |

## Seven cases when choosing `max_size=`

Upgrading alone keeps the behaviour in the middle column for all seven cases. The right column applies when you explicitly choose `max_size=` in Python. That choice also makes `merge` update the receiving digest.

| Input or operation | `delta=` or the default | `max_size=` |
| --- | --- | --- |
| Three NaNs | Skips all three. The digest is empty. | Rejects the NaNs. |
| `[10, 20, NaN]` | Keeps 10 and 20. | Rejects the array. |
| `[−∞, +∞, +∞]` | Keeps both infinities. The weight at +∞ is two. | Rejects infinities. |
| `[−∞, −20, 8, 10, +∞]` | Keeps all five values, including both infinities. | Rejects the array. |
| Merge `[−∞, 1, 2, +∞, +∞]` with `[−∞, −∞, −1, 30, +∞, +∞]` | Combines the repeated infinities and returns six centroids. | Rejects both arrays before the merge. |
| Build from a Float16 NumPy array | Raises `TypeError`. Accepts Float32 and Float64 arrays. | Accepts Float16. Stores means as Float64 by default. |
| Merge digests built from Float32 and Float64 arrays | Each digest takes its precision from the array. Merging the two raises `TypeError`. | Both default to Float64, so the merge succeeds with Float64 means. |

If you explicitly chose different precisions with `max_size=`, convert before merging. For a Float32 result, use `left.cast_precision("f32").merge(right.cast_precision("f32"))`. The compression settings must also agree.

## Reproduce the comparisons

<details>
<summary>Time median, percentile and merge calls</summary>

The Python test queried one digest built from a million shuffled Float64 values. It returned 499,999.5 for the median and 989,999.5 for the 99th percentile on both wheels. For the merge we built a second digest from the next million values. We checked the centroid means and weights byte for byte for both inputs and the result. Construction, validation of the benchmark results and file access took place outside the timed calls.

The older implementation totals the weights for each query. Version 1.0 already holds the total. Its Python merge at unchanged `delta` copies both native digests and checks their state before combining them. Version 0.1.0 merges the two sorted sets of means and weights directly. The measurements cover the complete public calls, including the Python bindings. [0.1.0 calculations](https://github.com/G-Research/tdigest-rs/blob/8d9cf1fe82c5c9254e5dc9593f01717e317f4333/src/core.rs), [1.0 merge binding](src/py.rs) and [timing script](docs/upstream-1.0.0/query_timings.py)

The Polars test used 256 groups of 4,096 observations with `max_size=200`. One lazy query computed both statistics per group. The timing includes collecting the result, and each group's answers were checked against the Python API. Polars 1.44.2 ran on the release wheel. For both experiments we report the median of seven timing rounds for each seed, then the median across seeds 42, 43 and 44.

Set `OLD_PY` and `PR_PY` to the Python executables for the two wheels. Install the Polars extra in the 1.0 environment. The Python comparison used CPython 3.12.15 and NumPy 1.26.4. Run these commands from the repository root, choosing CPU IDs available on your host.

```bash
queries=docs/upstream-1.0.0/query_timings.py
for seed in 42 43 44; do
  interpreters=("$OLD_PY" "$PR_PY")
  if [[ "$seed" == 43 ]]; then interpreters=("$PR_PY" "$OLD_PY"); fi
  for py in "${interpreters[@]}"; do
    taskset -c 8 "$py" -I "$queries" python --seed "$seed"
  done
  POLARS_MAX_THREADS=1 taskset -c 8 "$PR_PY" -I "$queries" polars --seed "$seed"
  POLARS_MAX_THREADS=8 taskset -c 8-15 "$PR_PY" -I "$queries" polars --seed "$seed"
done
```

</details>

<details>
<summary>Run the published benchmark, compare accuracy and time the same centroids</summary>

For seeds 42, 43 and 44, the original benchmark reported 2.576, 2.521, 2.506 seconds on 0.1.0 and 2.895, 2.997, 2.896 seconds on 1.0, in that order.

Run from the repository root in Bash. Set `OLD_PY` and `PR_PY` to the Python executables for two separate environments with 0.1.0 and 1.0 installed. Set `OLD_WHEEL` and `PR_WHEEL` to the corresponding wheel files. Use the same versions of NumPy and joblib in both. The recorded comparison used an AMD Ryzen 9 9950X3D on Linux with Python 3.12.15, NumPy 1.26.4 and joblib 1.5.2.

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
bench=tests/upstream_legacy/bindings/python/benchmarks/run.py
for seed in 42 43 44; do
  interpreters=("$OLD_PY" "$PR_PY")
  if [[ "$seed" == 43 ]]; then interpreters=("$PR_PY" "$OLD_PY"); fi
  for py in "${interpreters[@]}"; do
    "$py" -I -c 'import numpy as np,runpy,sys; np.random.seed(int(sys.argv[1])); runpy.run_path(sys.argv[2],run_name="__main__")' "$seed" "$bench"
  done
done

# Compare individual operations.
"$PR_PY" scripts/benchmark_upstream.py --rounds 7 \
  --baseline-python "$OLD_PY" --baseline-wheel "$OLD_WHEEL" \
  --candidate-python "$PR_PY" --candidate-wheel "$PR_WHEEL" \
  --output-dir build/wheel-comparison

mkdir -p build/accuracy
compare=docs/upstream-1.0.0/compare_recorded.py
"$OLD_PY" -I "$compare" delta > build/accuracy/published-delta.csv
"$PR_PY" -I "$compare" delta --save-centroids build/accuracy-centroids > build/accuracy/pr-delta.csv
"$OLD_PY" -I "$compare" delta --query-centroids build/accuracy-centroids > build/accuracy/published-query-on-pr-centroids.csv
"$PR_PY" -I "$compare" capacity > build/accuracy/pr-capacity.csv
```

```bash
matched=docs/upstream-1.0.0/matched_centroids.py
for seed in 42 43 44; do
  fixtures="build/matched-centroids/$seed"
  "$OLD_PY" -I "$matched" prepare "$fixtures" --seed "$seed"
  interpreters=("$OLD_PY" "$PR_PY")
  if [[ "$seed" == 43 ]]; then interpreters=("$PR_PY" "$OLD_PY"); fi
  for workers in 32 1; do
    for py in "${interpreters[@]}"; do
      "$py" -I "$matched" time "$fixtures" --seed "$seed" --workers "$workers"
    done
  done
  for py in "${interpreters[@]}"; do
    taskset -c 8 "$py" -I "$matched" million "$fixtures" --seed "$seed"
  done
done
```

The `prepare` step uses the published 0.1.0 wheel to record the reference centroids. The final loop pins the million value build to CPU 8. Choose an available CPU if you run it on a different machine.

</details>

<details>
<summary>Where the code, data and reference results came from</summary>

The shared Rust implementation came from the development repository. The original Python tests and benchmark are exact copies from G Research commit `8d9cf1f`. The manifest records their paths and checksums. [Rust source revision](https://github.com/ingolfured/gr-tdigest/commit/0eaa79411d1ca46cd0cf7294b03b6aafaf1a120c) and [original test manifest](tests/upstream_legacy/manifest.json)

We generated the 70 numerical reference cases by building the original `tdigest_core` with Rust 1.90.0 on Linux. To regenerate them, build the generator against that revision with `serde_json`. The pickle tests record which published wheel wrote each saved state. The Rust comparison records its dependencies, sources and results. [Numerical test generator](compat/numerical-parity/generate.rs), [pickle test records](compat/published-pickle/PROVENANCE.json) and [Rust reference manifest](compat/numerical-review/original-rust/oracle/source-manifest.json)

The accuracy tests use all rows from both recorded datasets. Their licenses, credits and preparation steps are stored with the data. The Spark interoperability test records its runtime and the artifact it tested. [Dataset credits](tests/quality/data/README.md) and [Spark run details](compat/spark-20261021/receipt.json)

</details>
