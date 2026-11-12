# Upgrading to `tdigest-rs` 1.0

We wanted to build one digest per service in Polars, find the percentile rank of every request, and let a Java service or a Python notebook query the same summary later. We also needed to know how much space those summaries would take as traffic grew. Polars, Python and Java now share the Rust code that builds and queries them.

**Existing NumPy callers can keep their `tdigest_rs` import, their `delta=` settings and their saved digests.** All 91 original Python tests passed unchanged before and after we installed 1.0 over the published 0.1.0 wheel on Linux. The upgrade test opened 32 pickles written by 0.1.0 and checked that each retained its total weight. Version 1.0 supports CPython 3.10 through 3.15. Polars is optional. [Upgrade test](scripts/test_package_upgrade.py)

## What you gain over 0.1.0

* **Percentile ranks in Polars.** The original Python API could tell you the latency at the 99th percentile. The new cumulative distribution function (CDF) answers the reverse question for a whole column in a lazy Polars query. Timing the rank lookup alone, Polars ranked 65,536 values against one digest in 1.699 ms on one CPU and 0.363 ms on eight. NumPy took 2.686 ms on one CPU. These are medians across six runs.
* **A fixed centroid budget per group.** Set `max_size=200` and the default policy keeps at most 200 centroids per digest after builds and merges. For 1,000 service groups, that gives you a ceiling of 200,000 centroids regardless of the number of requests. You can also choose among five scale functions to control where the digest keeps more detail.
* **Exact answers for repeated values that stay together.** A centroid records whether all its observations had the same value. If the requested rank falls inside the weight at that value, 1.0 returns it exactly. This matters for counts, rounded timings and other data with ties.
* **Updates to an existing summary.** With `max_size=`, you can add batches of values and counts, give older data less weight before merging it with a new batch, or convert stored latencies from milliseconds to seconds. These operations work on the digest itself. [Python API](README.md#python)
* **The same digest in Python, Rust and on the JVM.** Write a digest from Polars and open its bytes in Java, Kotlin or Scala. A Spark job can pass it between executors. The Rust CLI can build a digest from a CSV and query that same file format from the shell. [CLI example](README.md#rust-and-the-cli) and [JVM examples](bindings/java/README.md)

There are gains with the original settings too. At `delta=300`, average rank error fell in 102 of 108 comparisons on recorded data. The build from one million shuffled values took 30.27 ms in 1.0 and 107.75 ms in 0.1.0, with identical centroids. Merging digests that were already built took longer. [Accuracy results](#accuracy-with-the-existing-settings) and [timings by workload](#where-10-is-faster-and-where-it-is-slower)

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

Omitting the sizing argument still selects `delta=300`. Float32 and Float64 arrays keep their precision. Merging returns a new digest and leaves the originals available to query. We ran this example on both releases.

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

## Where 1.0 is faster and where it is slower

On one worker, building and merging 2,500 pairs took 2.656 s, down from 4.696 s. If the digests were already built, merging those same pairs took 0.396 s, up from 0.140 s. The difference matters most for a job that spends much of its time combining existing summaries.

| Workload | Workers | 0.1.0 | 1.0 |
| --- | ---: | ---: | ---: |
| Build from one million shuffled values | 1 | 107.75 ms | 30.27 ms |
| Build and merge 2,500 pairs | 1 | 4.696 s | 2.656 s |
| Build and merge 2,500 pairs | 32 | 0.221 s | 0.232 s |
| Merge the same 2,500 pairs of existing digests | 1 | 0.140 s | 0.396 s |
| Merge the same 2,500 pairs of existing digests | 32 | 0.045 s | 0.066 s |
| Run the original Python benchmark | 32 | 2.521 s | 2.954 s |

We ran both releases on the same machine and took the median across three seeds. Both releases produced exactly the same 146 centroids for the million value build. For the paired workloads, each input digest had 4,135 centroids and each merge produced 160. We checked every mean and weight against 0.1.0. In the original Python benchmark, 32 workers build digests at `delta=10000` and merge each with itself at `delta=300`. Version 1.0 took 17% longer in that run. Equal settings in this benchmark can produce different centroid counts.

Version 0.1.0 merges two lists that are already sorted. The 1.0 Python `delta=` merge used here collects the weighted values and sorts them in Rust. With `max_size=`, the Rust core can merge several sorted digests directly. The timings include the whole merge, so we cannot assign a share of the difference to sorting. For small arrays there is also a cost to checking the NumPy type, handling NaNs and choosing the constructor settings before calling Rust. [Timings for individual operations](docs/upstream-1.0.0/operation-timings.csv) and [earlier comparisons with matching centroids](docs/upstream-1.0.0/matched-timings.csv)

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
<summary>Run the published benchmark, compare accuracy and time the same centroids</summary>

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
