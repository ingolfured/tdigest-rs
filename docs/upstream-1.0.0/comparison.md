# Replacing tdigest-rs 0.1.0

The proposed Python delta API produced lower average rank error in **102 of 108** recorded-data cases. It built digests faster at every tested size from **1,000 to 1,000,000 observations**, in both precisions. The published wheel was faster on small inputs, on 40-way sequential merges and on the original threaded build-and-merge benchmark.

## The original benchmark

Both wheels ran the [unchanged upstream benchmark file](../../tests/upstream_legacy/bindings/python/benchmarks/run.py). It builds a digest at delta 10,000 from each of 5,000 Float64 arrays of length 16,000, then merges each digest with itself using the default merge delta of 300. It repeats this ten times with joblib’s threading backend and all 32 logical CPUs. The file times construction and merging together and excludes generating the arrays.

| Wall time | Published 0.1.0 | PR 1.0.0, same calls |
| --- | ---: | ---: |
| Seed 42 | 2.513 s | 3.956 s |
| Seed 43 | 2.614 s | 4.003 s |
| Seed 44 | 2.561 s | 4.048 s |
| **Median** | **2.561 s** | **4.003 s** |

The PR took **56% longer** on this workload. Each execution used a fresh Python process. Both wheels received the same arrays for each seed, and execution order alternated between pairs.

## Which operations got faster?

The [operation benchmark](../../scripts/benchmark_upstream.py) measures construction, queries and merges separately. These medians cover seven rounds on one CPU. Both columns below use the existing delta API with delta 300.

| Float64 operation | Published 0.1.0 | PR 1.0.0 |
| --- | ---: | ---: |
| Build from 32 values | 1.27 µs | 3.79 µs |
| Build from 1,000 values | 33.68 µs | 25.10 µs |
| Build from 10,000 values | 479 µs | 214 µs |
| Build from 100,000 values | 7.27 ms | 2.65 ms |
| Build from 1,000,000 values | 110.99 ms | 29.63 ms |
| Merge 40 digests of 1,000 values sequentially | 258 µs | 682 µs |
| Query p99 after building from 1,000,000 values | 170 ns | 136 ns |

The million-value construction speedup was **3.75× for Float64** and **3.63× for Float32**. Across the complete matrix, the PR had a lower median in **11 of 28** shared delta cases, including empty-input rejection. Some query medians differed by less than a nanosecond. The [individual round timings](operation-timings.csv) also include capacity-mode queries and operations added in 1.0.

The K2 merge optimization has a different baseline. With 40 prebuilt Float64 digests of 1,000 values each, capacity 1,000, sequential merging took **5.65 ms** in the PR and **18.79 ms** in the [earlier capacity implementation](https://github.com/ingolfured/tdigest-rs/commit/fa692858f6d36e94ef59c34b02349bc0f1575729). Both produced the same TDIG bytes. Those timings are medians of seven alternating rounds, twelve operations per round, on one CPU with NumPy seed 4242.

## Accuracy on recorded data

We ran both wheels on every row of the [bike-rental and household-energy datasets](../../tests/quality/data/README.md). Nine columns × two precisions × two input orders × three construction routes give **108 paired cases**. The routes were a single build, 40 sequential merges and a balanced tree of 40 digests. Each comparison uses the same observations cast to the same precision and the same 135 quantile probes.

Rank error is the distance between the requested percentile and the interval of ranks occupied by the returned value in the sorted input. This handles ties. Value error measures distance from the sample’s linearly interpolated quantile in that column’s original units.

| PR mode compared with published delta 300 | Lower mean rank error | Lower worst tail rank error | Lower mean value error |
| --- | ---: | ---: | ---: |
| Delta 300, same calls | 102 better, 6 worse | 104 better, 4 tied | 100 better, 8 worse |
| Capacity 1,000, K2 | 108 better | 108 better | 108 better |

Mean rank error across profiles fell from **0.46645 percentage points** to **0.04612** with delta 300 and **0.00172** with capacity 1,000. Tail probes cover the bottom and top 1%. Differences up to 1e-12 count as ties. The cases share datasets and are weighted equally. Capacities are different storage budgets. The [per-case results](recorded-accuracy.csv) give centroid counts and errors for all three configurations. The [earlier storage-matched study](../../tests/quality/ACCURACY.md) also covers synthetic distributions and cases where the original engine had lower value error.

## Reproduction

Tested on Linux x86-64, AMD Ryzen 9 9950X3D, CPython 3.12.15, NumPy 1.26.4 and joblib 1.5.2. The published Linux wheel’s SHA-256 is `62ee8d5a01226d020a2ab11a956292c38beab3f34d2d9fa7a8fca22c3e5d4bbf`. The [PR release wheel from commit 38fdc1e](https://github.com/ingolfured/tdigest-rs/actions/runs/42908349249) has SHA-256 `2ecb6784f32b574cee934e388ba4bc7742368c100153d0c847837ac44df6ca87`.

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
"$PR_PY" -I "$compare" delta > pr-delta.csv
"$PR_PY" -I "$compare" capacity > pr-capacity.csv
```
