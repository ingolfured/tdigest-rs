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

* **Percentile ranks in Polars.** The original Python API could tell you the latency at the 99th percentile. The new cumulative distribution function (CDF) answers the reverse question for a whole column in a lazy Polars query. We built one Float64 digest from 40,000 normal observations at `max_size=200`. It held 200 centroids. For 65,536 new observations, Polars took 1.70 ms on one logical CPU and 0.36 ms on eight. On one logical CPU the Python NumPy call took 2.67 ms. Both queried the same saved digest and returned identical ranks. Times exclude construction. [Query setup and measurements](#reproduce-the-comparisons)
* **A fixed centroid budget per group.** Set `max_size=200` and the default policy keeps at most 200 centroids per digest after builds and merges. For 1,000 service groups, that gives you a ceiling of 200,000 centroids regardless of the number of requests. You can also choose among five scale functions to control where the digest keeps more detail.
* **Exact answers for repeated values that stay together.** A centroid records whether all its observations had the same value. If the requested rank falls inside the weight at that value, 1.0 returns it exactly. This matters for counts, rounded timings and other data with ties.
* **Updates to an existing summary.** With `max_size=`, you can add batches of values and counts, give older data less weight before merging it with a new batch, or convert stored latencies from milliseconds to seconds. These operations work on the digest itself. [Python API](README.md#python)
* **The same digest in Python, Rust and on the JVM.** Write a digest from Polars and open its bytes in Java, Kotlin or Scala. A Spark job can pass it between executors. The Rust CLI can build a digest from a CSV and query that same file format from the shell. [CLI example](README.md#rust-and-the-cli) and [JVM examples](bindings/java/README.md)

On recorded data, **1.0 had lower average rank error in 102 of 108 comparisons where both releases kept exactly the same number of centroids.** For a build from one million shuffled Float64 integers, both used `delta=300` and produced the same 146 centroid means and weights. On one logical CPU, the build took 107.82 ms in 0.1.0 and 30.21 ms in 1.0. [Accuracy at equal centroid counts](#accuracy-at-equal-centroid-counts) and [build setup](#reproduce-the-comparisons)

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

## Accuracy at equal centroid counts

We gave 1.0 a limit of `max_size=128`, with its default K2 scale and singleton policy. Depending on the data, it kept **8 to 128 centroids**. For each case we chose the 0.1.0 `delta` using only the final centroid count. The selected values ranged from 5.859375 to 276.5625. We checked that the counts matched before comparing any estimates. All 108 pairs matched exactly. Each release chose its own centroid means and weights.

We used every row from four bike rental columns (17,379 rows each) and five energy columns (19,735 rows each). Each column was tested in Float32 and Float64, in forward and reverse order, with three ways to build the digest. We either built it in one pass, merged 40 parts in sequence, or merged 40 parts in pairs. We queried 135 probabilities against the sorted input. Rank error measures how far the answer falls from the requested percentile, allowing for ties. Value error measures the distance from the exact interpolated quantile in the column's own units.

| Measure across 108 pairs of equal size | Lower error in 1.0 | Same error | Higher error in 1.0 |
| --- | ---: | ---: | ---: |
| Average rank error | 102 | 0 | 6 |
| Worst rank error among queries at or below 1% and at or above 99% | 104 | 3 | 1 |
| Average value error | 104 | 0 | 4 |

All six increases in average rank error occurred on outdoor temperature. The largest was **0.011 percentage points** after merging 40 Float32 parts in pairs. Both digests held 128 centroids. Equal counts still leave each release free to group the observations differently and interpolate between the resulting means. The data records both settings, both counts and every error. [Results for each column and build](docs/upstream-1.0.0/recorded-accuracy.csv)

<details>
<summary>What happens if I keep delta at 300?</summary>

We also ran those 108 cases with `delta=300` on both wheels to measure the effect of upgrading existing code. Version 0.1.0 kept 138 to 272 centroids and 1.0 kept 8 to 254. Average rank error fell in 102 cases. The largest increase was 0.00335 percentage points. Those figures apply to keeping the same Python argument. The table above uses equal final counts. For a comparison by storage in bytes, the earlier study includes cases where 0.1.0 had smaller peak value errors. [Recorded results](docs/upstream-1.0.0/recorded-accuracy.csv) and [study with matched storage](https://github.com/ingolfured/tdigest-rs/blob/1292b6110578bb9561a168f0898254a62aaf1fcd/compat/quality-20261020/RESULTS.md)

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

We built each Float64 digest from the same million shuffled integers, then timed one public Python call on one logical CPU. **Every digest held 146 centroids.** The two `delta=300` digests also had identical means and weights. With `max_size=146`, 1.0 chose its own centroids. All three returned 499,999.5 for the median and 989,999.5 for the 99th percentile.

| Python call on a prebuilt digest | 0.1.0, `delta=300` | 1.0, `delta=300` | 1.0, `max_size=146` |
| --- | ---: | ---: | ---: |
| Median | 119 ns | 125 ns | 56 ns |
| 99th percentile | 157 ns | 124 ns | 75 ns |

We also timed a merge through the original Python API. Both wheels used `delta=300` and merged two digests with 146 centroids apiece. The left input, the right input and all 174 output centroids matched across releases, down to the last bit of every mean and weight. This merge took **3.26 µs in 0.1.0 and 9.25 µs in 1.0**. It includes the cost of copying and checking digests in the 1.0 Python binding. [Timing samples and centroid checksums](docs/upstream-1.0.0/query-timings.jsonl)

In Polars, one lazy query returned both statistics for 256 groups in **2.12 ms on eight logical CPUs** and 14.47 ms on one. Each group held 4,096 Float64 observations and its prebuilt digest contained exactly 200 centroids at `max_size=200`. This measures collecting the group results in 1.0. Version 0.1.0 had no native Polars query.

### The original Python benchmark

We ran the 0.1.0 benchmark unchanged on both wheels. It builds a digest from each of 5,000 arrays of 16,000 values at `delta=10000`, then merges each digest with itself at the default `delta=300`. The script repeats this ten times using 32 joblib threads. The 15,000 distinct Float64 arrays across our three seeds all produced 4,135 centroids before merging. The merged size was 160 in 0.1.0 and 158 in 1.0. This run measures the same Python calls with those two different output sizes. Array generation happens before the timer. [Original benchmark in 0.1.0](https://github.com/G-Research/tdigest-rs/blob/v0.1.0/bindings/python/benchmarks/run.py)

| Workload | 0.1.0 | 1.0 | Change |
| --- | ---: | ---: | --- |
| Original Python benchmark | 2.539 s | 2.907 s | 1.0 took 14.5% longer |

For an exact comparison, we also built 2,500 pairs from the same shuffled integer ranges on 32 joblib threads. Each digest held 4,135 centroids at `delta=10000`. Each pair merged to 160 at `delta=300`. Both wheels produced identical means and weights at both stages. Building and merging all pairs took **0.216 s in 0.1.0 and 0.231 s in 1.0**. We used a median of three passes per seed, then the median across the three seeds. [Times and centroid counts](docs/upstream-1.0.0/matched-timings.csv)

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

All timings used Linux on an AMD Ryzen 9 9950X3D and CPython 3.12.15. The comparisons between wheels used NumPy 1.26.4. The Polars runs used Polars 1.44.2 and NumPy 2.3.4. The Python test queried one digest built from a million shuffled Float64 values. It returned 499,999.5 for the median and 989,999.5 for the 99th percentile on both wheels. For the merge we built a second digest from the next million values. We checked the centroid means and weights byte for byte for both inputs and the result. Construction, validation of the benchmark results and file access took place outside the timed calls.

The older implementation totals the weights for each query. Version 1.0 already holds the total. Its Python merge at unchanged `delta` copies both native digests and checks their state before combining them. Version 0.1.0 merges the two sorted sets of means and weights directly. The measurements cover the complete public calls, including the Python bindings. [0.1.0 calculations](https://github.com/G-Research/tdigest-rs/blob/8d9cf1fe82c5c9254e5dc9593f01717e317f4333/src/core.rs), [1.0 merge binding](src/py.rs) and [timing script](docs/upstream-1.0.0/query_timings.py)

The Polars test used 256 groups of 4,096 observations with `max_size=200`. One lazy query computed both statistics per group. The timing includes collecting the result, and each group's answers were checked against the Python API. Polars 1.44.2 ran on the release wheel. All query timings report the median of seven rounds per seed, then the median across seeds 42, 43 and 44. Each round made 200,000 Python quantile or median calls, 3,000 Python merges, 25 grouped Polars queries or 18 CDF calls. For the CDF test each seed generated the training values and probes from independent draws of a standard normal distribution. Each API queried the same centroid data and probes.

Set `OLD_PY` and `PR_PY` to the Python executables for the two wheels. Set `POLARS_PY` to the 1.0 environment with the Polars extra and NumPy 2.3.4. The Python comparison used CPython 3.12.15 and NumPy 1.26.4. Run these commands from the repository root, choosing CPU IDs available on your host.

```bash
queries=docs/upstream-1.0.0/query_timings.py
for seed in 42 43 44; do
  interpreters=("$OLD_PY" "$PR_PY")
  if [[ "$seed" == 43 ]]; then interpreters=("$PR_PY" "$OLD_PY"); fi
  for py in "${interpreters[@]}"; do
    taskset -c 8 "$py" -I "$queries" python --seed "$seed"
  done
  taskset -c 8 "$PR_PY" -I "$queries" capacity --seed "$seed"
  for api in polars cdf; do
    POLARS_MAX_THREADS=1 taskset -c 8 "$POLARS_PY" -I "$queries" "$api" --seed "$seed"
    POLARS_MAX_THREADS=8 taskset -c 8-15 "$POLARS_PY" -I "$queries" "$api" --seed "$seed"
  done
done
```

</details>

<details>
<summary>Run the published benchmark, compare accuracy and time the same centroids</summary>

For seeds 42, 43 and 44, the original benchmark reported 2.487, 2.553, 2.539 seconds on 0.1.0 and 2.912, 2.907, 2.907 seconds on 1.0, in that order.

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
"$OLD_PY" -I "$compare" delta --match-counts build/accuracy/pr-capacity.csv > build/accuracy/matched-published.csv
```

```bash
matched=docs/upstream-1.0.0/matched_centroids.py
for seed in 42 43 44; do
  for py in "$OLD_PY" "$PR_PY"; do
    "$py" -I "$matched" original-counts --seed "$seed"
  done
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

The `prepare` step uses the published 0.1.0 wheel to record the reference centroids. The million value test times seven builds per seed on CPU 8 and verifies all centroid means and weights outside the timer. We take the median per seed and then the median of those three results. Choose an available CPU if you run it on a different machine.

</details>

<details>
<summary>Where the code, data and reference results came from</summary>

The shared Rust implementation came from the development repository. The original Python tests and benchmark are exact copies from G Research commit `8d9cf1f`. The manifest records their paths and checksums. [Rust source revision](https://github.com/ingolfured/gr-tdigest/commit/0eaa79411d1ca46cd0cf7294b03b6aafaf1a120c) and [original test manifest](tests/upstream_legacy/manifest.json)

We generated the 70 numerical reference cases by building the original `tdigest_core` with Rust 1.90.0 on Linux. To regenerate them, build the generator against that revision with `serde_json`. The pickle tests record which published wheel wrote each saved state. The Rust comparison records its dependencies, sources and results. [Numerical test generator](compat/numerical-parity/generate.rs), [pickle test records](compat/published-pickle/PROVENANCE.json) and [Rust reference manifest](compat/numerical-review/original-rust/oracle/source-manifest.json)

The accuracy tests use all rows from both recorded datasets. Their licenses, credits and preparation steps are stored with the data. The Spark interoperability test records its runtime and the artifact it tested. [Dataset credits](tests/quality/data/README.md) and [Spark run details](compat/spark-20261021/receipt.json)

</details>
