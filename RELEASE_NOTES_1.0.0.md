# Reviewing tdigest 1.0

We wanted to aggregate latency in Polars, ask where each observation falls in its group, and use the resulting digest from Java and Python. That called for a shared Rust implementation of compression and the cumulative distribution function (CDF). It also gave us one place to implement the scale functions used to allocate centroids near the tails. More centroids in a region let the digest resolve smaller differences in rank there.

## Rank each observation in Polars

```python
import polars as pl
import tdigest_rs as td

requests = pl.LazyFrame({
    "service": ["search", "search", "checkout", "checkout"],
    "latency_ms": [12.0, 48.0, 35.0, 90.0],
})
digests = requests.group_by("service").agg(
    td.tdigest("latency_ms", max_size=200).alias("digest")
)
ranked = requests.join(digests, on="service").select(
    "service", "latency_ms",
    td.cdf("digest", pl.col("latency_ms")).alias("percentile_rank"),
)
print(ranked.collect())
```

A probe at a tied value receives the mass strictly below it plus half the mass at that value, divided by total mass. The join lets one digest answer every probe for its group. Use a single CDF expression for a column of probes. Passing TDIG v3 bytes between Rust, Python, Polars and Java preserves the observed extrema, mean precision, weights and compression settings. Versions 1 and 2 remain readable.

## Upgrading Python from 0.1.0

Keep the existing import and constructor. The default is still `delta=300`. Both versions produce the same results for these assertions.

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

### Seven cases from the original tests

The original calling convention passes all 91 tests unchanged. The right column shows what happens if you explicitly select capacity mode.

| Input or operation | Existing calls (`delta=` or default) | With `max_size=` |
| --- | --- | --- |
| Three NaNs | Skips all three and returns an empty digest. | Rejects NaN during construction. |
| `[10, 20, NaN]` | Keeps 10 and 20. | Rejects the array because it contains a NaN. |
| `[-∞, +∞, +∞]` | Stores two endpoints, with weight two at +∞. | Rejects infinite training values. |
| `[-∞, -20, 8, 10, +∞]` | Keeps all five means, including the endpoints. | Rejects the array because it contains infinities. |
| Merge `[-∞, 1, 2, +∞, +∞]` with `[-∞, -∞, -1, 30, +∞, +∞]` | Combines repeated endpoints and returns six centroids. | Construction rejects each input before the merge. |
| A Float16 NumPy array | Raises `TypeError`. The original API accepts Float32 and Float64 arrays. | Accepts Float16 input. Default mean storage is Float64. |
| Merge digests built from Float32 and Float64 arrays | The arrays select different stored precisions, so a direct merge raises `TypeError`. | Both constructors default to Float64, so the merge succeeds with Float64 means. If you choose different stored precisions, cast explicitly before merging. |

For a Float32 merge, use `left.cast_precision("f32").merge(right.cast_precision("f32"))` with compatible compression settings.

### Numerical changes

The old 10th percentile of `[1.0, 2.0]` was approximately 0.7. The shared core returns the observed minimum, 1.0. The median of `[0.0, 10.0]` with weights `[90, 10]` changes from 1.0 to 0.0, where 90 percent of the mass lies. Original pickles store means and weights. Loading one rebuilds the digest and queries use the new interpolation. The migration tests cover 32 states from the published wheel. Rust consumers of the original `tdigest_core` crate should switch to the root `tdigest-rs` crate and handle checked operations.

## Accuracy on recorded data

We compared both wheels on nine columns of bike rental and energy data, in both precisions and input orders. Each case used one bulk build, 40 sequential merges or a balanced tree of 40 digests. Against 0.1.0 at delta 300, the 1.0 delta API had lower mean rank error in 102 of 108 cases. The six losses came from merged outdoor temperature summaries. Replaying the old query formula on the new centroids still produced higher error than the old digest. Compression changed their placement and count. The evidence does not distinguish their individual contributions. Eight cases had higher mean error in the original units. Capacity 1,000 improved all 108 cases but uses a different storage budget. [Per case counts, errors and query replay](docs/upstream-1.0.0/recorded-accuracy.csv)

The extended regression suite compares 756 profiles against frozen measurements. Ten synthetic profiles exceed documented accuracy targets. An earlier comparison matched storage and found larger peak value errors on the energy data and better results for the original algorithm on several synthetic distributions. [Accuracy limits](tests/quality/known-limits.json) and [original study](https://github.com/ingolfured/tdigest-rs/blob/1292b6110578bb9561a168f0898254a62aaf1fcd/compat/quality-20261020/RESULTS.md)

## Timing the same work

We ran the published 0.1.0 wheel, the starting 1.0 wheel at `1292b61` and the revised 1.0 wheel on the same host. Cells are median wall times across seeds 42, 43 and 44. The first row uses the original threaded benchmark. The other rows verify each centroid mean and weight before timing.

| Workload | Published 0.1.0 | Starting 1.0 | Revised 1.0 |
| --- | ---: | ---: | ---: |
| Original benchmark, 32 workers | 2.521 s | 3.988 s | 2.954 s |
| Merge 2,500 prebuilt pairs, one worker | 0.140 s | 0.420 s | 0.396 s |
| Merge 2,500 prebuilt pairs, 32 workers | 0.045 s | 0.120 s | 0.066 s |
| Build and merge the same pairs, one worker | 4.696 s | 2.693 s | 2.656 s |
| Build and merge the same pairs, 32 workers | 0.221 s | 0.285 s | 0.232 s |
| Build a million shuffled observations, one worker | 107.75 ms | 30.26 ms | 30.27 ms |

The original benchmark builds at delta 10,000 and merges at 300. The revised merge reads centroids in Rust and releases the Python interpreter lock during compression. On a single merge of a digest with 4,135 centroids, peak memory visible to Python's allocation tracer fell from 199,000 to 513 bytes. This measures Python and NumPy allocations only. Rust still allocates storage for weighted observations and sorts them. The published implementation merges its ordered centroid runs directly. The revised 1.0 benchmark still took 17 percent longer than 0.1.0, and the matched merge by itself was also slower. These timings do not isolate how much of that remaining difference comes from sorting.

In the matched pair workload, both builds produce 4,135 centroids and each pair merge produces 160. The million value build produces 146 identical centroids. The original threaded workload has equal settings but can produce different counts across 0.1.0 and 1.0. Earlier operation timings also show the small array cost: on 32 values, the 1.0 Python adapter checks dtype, filters nonfinite values and resolves options before calling Rust. [Historical operation timings](docs/upstream-1.0.0/operation-timings.csv) and [historical matched runs](docs/upstream-1.0.0/matched-timings.csv)

A separate comparison of the two 1.0 wheels timed 40 sequential merges of 1,000 observations each on one CPU. The median fell from 671 to 617 microseconds. The shared core now borrows the existing centroid runs after checking their configuration and state. Across all 108 recorded profiles in each of the two calling modes, centroid counts and reported error metrics matched exactly.

For 65,536 random probes against one digest, six runs on one CPU gave 2.671 ms before and 2.686 ms after in NumPy, and 1.686 ms before and 1.699 ms after in Polars. With eight CPUs the Polars times were 0.362 and 0.363 ms. The returned ranks matched. An intermediate build retaining the old query loop took 1.695 ms for Polars on one CPU. The measurements do not isolate a cause for differences this small.

## Reproduce the comparisons

Use separate Python environments for each release wheel with the same NumPy and joblib versions. Set `OLD_PY` to the published 0.1.0 Python executable and `PR_PY` to the candidate executable. For a comparison within 1.0, use the starting 1.0 Python executable in place of `OLD_PY` for timing. Keep the published executable for the `prepare` command. The operation benchmark below uses 0.1.0 as its baseline. Run from the repository root. The historical comparison used an AMD Ryzen 9 9950X3D on Linux, Python 3.12.15, NumPy 1.26.4 and joblib 1.5.2.

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


# Set OLD_WHEEL and PR_WHEEL to the corresponding wheel files.
"$PR_PY" scripts/benchmark_upstream.py --rounds 7 \
  --baseline-python "$OLD_PY" --baseline-wheel "$OLD_WHEEL" \
  --candidate-python "$PR_PY" --candidate-wheel "$PR_WHEEL" \
  --output-dir build/wheel-comparison

compare=docs/upstream-1.0.0/compare_recorded.py
"$OLD_PY" -I "$compare" delta > published-delta.csv
"$PR_PY" -I "$compare" delta --save-centroids build/accuracy-centroids > pr-delta.csv
"$OLD_PY" -I "$compare" delta --query-centroids build/accuracy-centroids > published-query-on-pr-centroids.csv
"$PR_PY" -I "$compare" capacity > pr-capacity.csv
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

## Source and fixture provenance

The shared Rust code came from [the development repository](https://github.com/ingolfured/gr-tdigest/commit/0eaa79411d1ca46cd0cf7294b03b6aafaf1a120c). The original suite and benchmark retain their bytes from G Research commit `8d9cf1fe82c5c9254e5dc9593f01717e317f4333`. Their manifest records every original path and checksum. [Original suite manifest](tests/upstream_legacy/manifest.json)

The 70 numerical fixtures came from a separate build of that revision with Rust 1.90.0 on Linux. To reproduce them, build the generator against that original `tdigest_core` and `serde_json`. The pickle fixtures have their own published wheel identity and generator. Historical Rust measurements retain the dependency lock, source manifest and recorded outputs. [Numerical generator](compat/numerical-parity/generate.rs), [pickle provenance](compat/published-pickle/PROVENANCE.json) and [Rust reference manifest](compat/numerical-review/original-rust/oracle/source-manifest.json)

The quality suite reads all rows from two locally stored datasets. Their attribution, licenses and preparation steps are kept beside the data. The Spark interoperability run records its runtime and artifact identity separately. [Dataset credits](tests/quality/data/README.md) and [Spark receipt](compat/spark-20261021/receipt.json)
