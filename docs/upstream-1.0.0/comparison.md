# Comparing 1.0 with 0.1.0

The 1.0 Python delta API produced lower average rank error in **102 of 108** cases on recorded data. It built digests faster at every tested size from **1,000 to 1,000,000 observations**, in both precisions. The published wheel was faster on small inputs, when merging 40 digests in sequence and on the original threaded benchmark for building and merging digests.

## The original benchmark with the same API calls

Both wheels ran the [unchanged upstream benchmark file](../../tests/upstream_legacy/bindings/python/benchmarks/run.py). It builds a digest at delta 10,000 from each of 5,000 Float64 arrays of length 16,000, then merges each digest with itself using the default merge delta of 300. It repeats this ten times with joblib's threading backend and all 32 logical CPUs. The file times construction and merging together and excludes generating the arrays.

| Wall time | Published 0.1.0 | PR 1.0.0, same calls |
| --- | ---: | ---: |
| Seed 42 | 2.513 s | 3.956 s |
| Seed 43 | 2.614 s | 4.003 s |
| Seed 44 | 2.561 s | 4.048 s |
| **Median** | **2.561 s** | **4.003 s** |

The PR took **56% longer** on this workload. Each execution used a fresh Python process. Both wheels received the same arrays for each seed, and execution order alternated between pairs. Both built 4,135 centroids from each input. For the example from seed 42, merging at the default delta produced 160 centroids on 0.1.0 and 158 on 1.0. Equal delta alone does not guarantee equal output.

## Comparing the same centroids

**Identical centroid means and weights.** We used 2,500 pairs of independently shuffled Float64 arrays. Each pair contains the integers 0 to 15,999 in one array and 16,000 to 31,999 in the other. Both versions use the same API and deltas. Each build at delta 10,000 produces 4,135 centroids. Each pair merge at delta 300 produces 160. Every centroid mean and weight was checked byte for byte against the published wheel before timing. The combined run builds both digests and merges them.

| Operation | Workers | Published 0.1.0 | PR 1.0.0 |
| --- | ---: | ---: | ---: |
| Build 5,000 digests | 1 | 4.676 s | 2.283 s |
| Merge 2,500 prebuilt pairs | 1 | 0.140 s | 0.426 s |
| Build and merge 2,500 pairs | 1 | 4.705 s | 2.678 s |
| Build 5,000 digests | 32 | 0.227 s | 0.223 s |
| Merge 2,500 prebuilt pairs | 32 | 0.045 s | 0.130 s |
| Build and merge 2,500 pairs | 32 | 0.217 s | 0.285 s |

On one worker the 1.0 builds are quicker and the complete workload takes **43% less time**. With 32 workers build times are similar and the complete workload takes **32% longer**. Stages were timed in separate runs, each with its own joblib dispatch. The combined rows time both operations in the same callback.

A separate build on one core using one million shuffled, distinct Float64 integer values at delta 300 produced **146 centroids that matched byte for byte** on both wheels. It took **109.18 ms** on 0.1.0 and **30.21 ms** on 1.0, a **3.61× speedup**.

**Merging each digest with itself at equal output count.** For each of the original 5,000 normal arrays, we saved the 0.1.0 digest's 4,135 means and weights. Both wheels reconstructed those exact bytes before timing. A merge delta of 304 on **both** wheels gives 161 output centroids for every pair, with total weight 32,000. The output means and weights differ between wheels in this case. Timing just these merges gave **0.097 s vs 0.225 s** at 32 workers and **0.394 s vs 0.749 s** with one worker (0.1.0 then 1.0).

**Why this merge costs more.** The input digest's delta is 10,000 and the output delta is different. The [0.1.0 merge](https://github.com/G-Research/tdigest-rs/blob/v0.1.0/src/core.rs#L37-L53) combines the two sorted centroid sequences in Rust. The [1.0 delta adapter](../../bindings/python/tdigest_rs/tdigest_rs.py) copies each input's means and weights into NumPy, concatenates them, and calls the weighted constructor. Rust copies those arrays back and sorts the pairs of values and weights before compression. In a separate run with 32 workers, seed 42 and 5,000 digests each merged with itself at delta 300, the full 1.0 merge took 227 ms. Timing just the weighted constructor on preassembled arrays took 142 ms. This identifies the copies between Rust and NumPy and the weighted rebuild as targets for a native merge that accepts an output delta.

All results use the wheels and machine listed below. The timings with matching centroids are medians across seeds 42, 43 and 44, alternating which wheel ran first. Each seed uses three passes for 32 workers, one for a single worker, and seven passes on one pinned CPU for the build from one million values. Setup and centroid verification are outside the timers. [Timings by seed](matched-timings.csv) · [Verification and benchmark code](matched_centroids.py)

## Which operations got faster?

The [operation benchmark](../../scripts/benchmark_upstream.py) measures construction, queries and merges separately. These medians cover seven rounds on one CPU. Both columns below use the existing delta API with delta 300.

| Float64 operation | Published 0.1.0 | PR 1.0.0 | Centroids (0.1.0 / 1.0) |
| --- | ---: | ---: | ---: |
| Build from 32 values | 1.27 µs | 3.79 µs | 32 / 31 |
| Build from 1,000 values | 33.68 µs | 25.10 µs | 128 / 119 |
| Build from 10,000 values | 479 µs | 214 µs | 137 / 132 |
| Build from 100,000 values | 7.27 ms | 2.65 ms | 142 / 138 |
| Build from 1,000,000 values | 110.99 ms | 29.63 ms | 146 / 142 |
| Merge 40 digests of 1,000 values sequentially | 258 µs | 682 µs | 278 / 269 |
| Query p99 after building from 1,000,000 values | 170 ns | 136 ns | 146 / 142 |

The speedup for building from one million values was **3.75× for Float64** and **3.63× for Float32**. Across the complete matrix, the PR had a lower median in **11 of 28** shared delta cases, including the time to reject empty input. Some query medians differed by less than a nanosecond. The [individual round timings](operation-timings.csv) also include queries using capacity mode and operations added in 1.0.

Building from 32 values spends much of its time in the Python adapter. In a separate run on the same finite array, the full 1.0 call took 3.73 µs. Calling the native constructor directly took 1.30 µs and produced the same means and weights. The corresponding 0.1.0 times were 1.22 µs and 0.94 µs. The 1.0 adapter checks dtype, scans for nonfinite values and resolves constructor options on each call. Those fixed costs matter more for an array with only 32 values.

The test that merges 40 digests in sequence uses the same delta for every input and output. This takes a different path from the original threaded benchmark. To return a new digest on each of the 39 merges, the 1.0 binding clones the native inputs and checks the merged state. Repeating that work on the growing accumulator adds cost. The timing covers cloning, validation and compression together, so their individual shares are unknown. [Python merge paths](../../bindings/python/tdigest_rs/tdigest_rs.py) · [Native merge implementation](../../src/py.rs)

The K2 merge optimization has a different baseline. With 40 prebuilt Float64 digests of 1,000 values each, capacity 1,000, sequential merging took **5.65 ms** in the PR and **18.79 ms** in the [earlier capacity implementation](https://github.com/ingolfured/tdigest-rs/commit/fa692858f6d36e94ef59c34b02349bc0f1575729). Both produced the same TDIG bytes. Those timings are medians of seven alternating rounds, twelve operations per round, on one CPU with NumPy seed 4242.

## Accuracy on recorded data

We ran both wheels on every row of the [bike rental and household energy datasets](../../tests/quality/data/README.md). Nine columns × two precisions × two input orders × three construction routes give **108 paired cases**. The routes were a single build, 40 sequential merges and a balanced tree of 40 digests. Each comparison uses the same observations cast to the same precision and the same 135 quantile probes.

Rank error is the distance between the requested percentile and the interval of ranks occupied by the returned value in the sorted input. This handles ties. Value error measures distance from the sample's linearly interpolated quantile in that column's original units.

| PR mode compared with published delta 300 | Lower mean rank error | Lower worst tail rank error | Lower mean value error |
| --- | ---: | ---: | ---: |
| Delta 300, same calls | 102 better, 6 worse | 104 better, 4 tied | 100 better, 8 worse |
| Capacity 1,000, K2 | 108 better | 108 better | 108 better |

Mean rank error across profiles fell from **0.46645 percentage points** to **0.04612** with delta 300 and **0.00172** with capacity 1,000. Tail probes cover the bottom and top 1%. Differences up to `1e-12` count as ties. The cases share datasets and are weighted equally. Capacities are different storage budgets. The [individual results](recorded-accuracy.csv) give centroid counts and errors for all three configurations. The [earlier study at matched storage](../../tests/quality/ACCURACY.md) also covers synthetic distributions and cases where the original engine had lower value error.

### Where 0.1.0 was more accurate

All six higher mean rank errors at delta 300 were on **outdoor temperature after 40 partial digests were merged**. In each case 1.0 kept fewer centroids (238 to 254, compared with 251 to 268 on 0.1.0). To distinguish compression from the query formula, we gave the published wheel the 1.0 means and weights, verified that it retained every byte, and queried the same 135 probabilities. **In all six cases, the old query on the new centroids already had higher error than the old query on the old centroids.** Switching to the 1.0 query on those same centroids reduced the error slightly in all six. The losses came from the merged centroid distribution. Both count and placement changed, so their individual contributions remain unknown.

For example, in the Float64 forward sequential merge, the exact 48.4375th percentile was 6.6833 °C. The original digest returned 6.6894 °C. Both query formulas returned 6.7003 °C on the 1.0 centroids. Many observations are close together there, so a small temperature difference crosses several ranks.

Mean **value** error was higher in eight cases. Two came from merging bicycle rental counts sequentially after reversing the input order. Replaying the old query on the new centroids made the error worse in both, and the new query recovered part of that loss. The other six were outdoor temperature. In four, changing the centroids already worsened mean value error. In two, the old query on the new centroids improved it, but the change in interpolation reversed that gain. For the forward Float64 balanced merge, the exact 99.99th percentile was 25.9684 °C. On the same centroids the old query returned 26.0018 °C and 1.0 returned the observed value 26.0333 °C. That answer scores better on rank and worse against a linearly interpolated reference in degrees. The replay columns in the [individual results](recorded-accuracy.csv) show both error measures for every case.

## Reproduction

Tested on Linux on `x86_64`, AMD Ryzen 9 9950X3D, CPython 3.12.15, NumPy 1.26.4 and joblib 1.5.2. The published Linux wheel's `SHA-256` is `62ee8d5a01226d020a2ab11a956292c38beab3f34d2d9fa7a8fca22c3e5d4bbf`. The [PR release wheel from commit 38fdc1e](https://github.com/ingolfured/tdigest-rs/actions/runs/42908349249) has `SHA-256` `2ecb6784f32b574cee934e388ba4bc7742368c100153d0c847837ac44df6ca87`.

Use separate virtual environments with the two wheels and matching dependencies. From the repository root, set `OLD_PY` and `PR_PY` to their Python executable paths, and `OLD_WHEEL` and `PR_WHEEL` to the wheel paths.

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

For the runs with matching centroids, prepare each seed once with 0.1.0. Both wheels read the same fixtures. The script checks the states outside the timed sections. The build from one million values uses CPU 8 on the benchmark host.

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
