# Historical performance comparison

These measurements compare the dual engine development revision below with the published 0.1.0 wheel. For timings of the shared core in this PR, see the [current wheel comparison](comparison.md).

Measured on 6 November 2026. The numerical implementation was built from upstream adaptation commit `0c94d899cfd2a63d19ab158084cc38dc1273a575`, based on development master `0eaa79411d1ca46cd0cf7294b03b6aafaf1a120c`. The benchmark harness subsequently corrected its empty input and merge in place handling; the version accompanying this report produced these results. The package implementation did not change.

## What the measurements support

- Existing legacy construction at one million observations is 3.48× faster for Float32 and 3.92× for Float64. Legacy centroid/weight bytes match the published wheel across every measured case and all seven rounds.
- Existing legacy median queries at that size are 1.77 to 1.86× slower, and queries for the 99th percentile are 1.44 to 1.47× slower. Small construction and merge changes are mixed; sample ranges matter.
- In the measured build, capacity compression was optional. At capacity 1,000, merging 40 children of 1,000 observations takes about 19 ms versus 0.24 to 0.26 ms for published legacy at delta 300: about 73 to 80× slower. `merge_all` has a similar cost here. This is a material limitation for the stated merge workload.
- Modern uses more centroid storage at these settings and has a smaller rank error on the three sampled quantiles. These are unequal storage/accuracy budgets, not a claim of algorithmic superiority. That build still routed existing calls to a separate implementation.

## Reproduction and artifacts

Run [`scripts/benchmark_upstream.py`](../../scripts/benchmark_upstream.py) with separate clean environments containing the respective wheels and the same Python/NumPy versions:

```sh
python scripts/benchmark_upstream.py \
  --baseline-python /path/to/published-venv/bin/python \
  --candidate-python /path/to/candidate-venv/bin/python \
  --baseline-wheel /path/to/published.whl \
  --candidate-wheel /path/to/candidate.whl \
  --output-dir /path/to/new-results --rounds 7
```

Host: AMD Ryzen 9 9950X3D, Linux x86_64, logical CPU 8 affinity, boost enabled; CPython 3.12.15 and NumPy 1.26.4. Rayon/OpenBLAS/OMP thread limits are 1. Local compilation and test workloads had finished before timing. All timings came from this workstation.

| Artifact | SHA256 |
| --- | --- |
| baseline: `tdigest_rs-0.1.0-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | `62ee8d5a01226d020a2ab11a956292c38beab3f34d2d9fa7a8fca22c3e5d4bbf` |
| candidate: `tdigest_rs-1.0.0-cp310-abi3-manylinux_2_28_x86_64.whl` | `704f5f2fce2e2edc16a3f60ff0f4829e096a772f38372a15fc79a2cddf9cc100` |

Candidate: release wheel compiled once using CPython 3.10 from the checked 1.0.0 source archive, with the locked Rust 1.95.0 dependencies and Zig manylinux_2_28 build. Baseline: authentic PyPI 0.1.0 manylinux2014 wheel. Different compiler/build generations are part of this package level comparison; it does not isolate which optimization caused the speed change.

Each of seven rounds rotates/reverses the order of three isolated processes (published legacy, candidate legacy, candidate modern). Each case warms up, then adaptively batches operations targeting 25 ms, capped at 20,000 iterations; expensive operations may have only one iteration per round. GC is disabled during timing. Setup is outside timing; construction/merge result destruction is included. All seven sample values are retained in [`performance.json`](performance.json); the ranges below are observed minima/maxima, not confidence intervals.

Inputs use seed 4242, normal values with a shifted 10% component and repeated -2 points; child seeds increment. Both precisions are explicit. Legacy uses delta 300; modern uses capacity 1,000, default K2 and singleton `Use`. Sequential merge copies the first child, then merges 39 others, respecting legacy return value and modern in place semantics. Child construction is outside the merge timer. Modern `merge_all` includes all 40 children. Queries reuse one digest.

## Full timings

All timings are **microseconds per operation**, shown as median [minimum to maximum]. Speed ratio is published legacy / candidate; >1 means faster. Merge size denotes observations **per child**, with 40 children. Empty legacy construction is rejection timing; it is not comparable to successful modern empty construction.

### F32

| Case / input size | Published legacy µs | Candidate legacy µs | Legacy ratio | Optional modern µs | Modern ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| `reject_empty/0` | 0.528 [0.520 to 0.674] | 0.506 [0.502 to 0.565] | 1.04× | N/A | N/A |
| `build/1` | 0.540 [0.537 to 0.677] | 0.530 [0.529 to 0.546] | 1.02× | 1.085 [1.069 to 1.094] | 0.497× |
| `build/32` | 1.214 [1.196 to 1.541] | 1.048 [1.040 to 1.054] | 1.16× | 2.147 [2.128 to 2.168] | 0.565× |
| `build/1000` | 33.416 [33.316 to 56.336] | 13.334 [13.310 to 13.370] | 2.51× | 30.628 [30.457 to 30.821] | 1.091× |
| `median/1000` | 0.109 [0.107 to 0.147] | 0.166 [0.164 to 0.176] | 0.66× | 0.780 [0.771 to 0.850] | 0.140× |
| `quantile_99/1000` | 0.194 [0.188 to 0.236] | 0.229 [0.225 to 0.234] | 0.85× | 1.567 [1.540 to 1.585] | 0.124× |
| `build/10000` | 467.619 [466.428 to 519.663] | 157.908 [157.724 to 163.061] | 2.96× | 807.568 [804.735 to 814.217] | 0.579× |
| `build/100000` | 6862.803 [6809.794 to 6905.256] | 2264.735 [2259.022 to 2274.656] | 3.03× | 3494.465 [3488.142 to 3565.329] | 1.964× |
| `build/1000000` | 100576.778 [100345.563 to 103385.274] | 28887.463 [28677.010 to 29310.335] | 3.48× | 29143.784 [28852.849 to 29516.141] | 3.451× |
| `median/1000000` | 0.112 [0.112 to 0.114] | 0.208 [0.197 to 0.215] | 0.54× | 0.255 [0.253 to 0.263] | 0.441× |
| `quantile_99/1000000` | 0.166 [0.163 to 0.191] | 0.245 [0.240 to 0.250] | 0.68× | 0.358 [0.354 to 0.371] | 0.464× |
| `merge_sequential_40/32` | 117.993 [117.480 to 118.353] | 114.285 [113.249 to 114.641] | 1.03× | 2714.075 [2706.041 to 2728.143] | 0.043× |
| `merge_sequential_40/1000` | 244.714 [243.736 to 245.797] | 230.438 [229.041 to 238.142] | 1.06× | 19477.109 [19433.147 to 19526.802] | 0.013× |
| `merge_sequential_40/10000` | 289.113 [287.424 to 290.299] | 272.857 [270.626 to 298.219] | 1.06× | 19473.562 [19441.953 to 19512.375] | 0.015× |
| `build/0` | No equivalent | N/A | N/A | 0.976 [0.964 to 1.002] | N/A |
| `cdf_zero/1000` | No equivalent | N/A | N/A | 2.129 [2.126 to 2.150] | N/A |
| `cdf_zero/1000000` | No equivalent | N/A | N/A | 2.200 [2.193 to 2.249] | N/A |
| `merge_all_40/32` | No equivalent | N/A | N/A | 2704.515 [2700.665 to 3600.411] | N/A |
| `merge_all_40/1000` | No equivalent | N/A | N/A | 19468.342 [19434.279 to 27227.476] | N/A |
| `merge_all_40/10000` | No equivalent | N/A | N/A | 19508.757 [19448.334 to 19534.827] | N/A |

### F64

| Case / input size | Published legacy µs | Candidate legacy µs | Legacy ratio | Optional modern µs | Modern ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| `reject_empty/0` | 0.556 [0.548 to 0.564] | 0.530 [0.519 to 0.561] | 1.05× | N/A | N/A |
| `build/1` | 0.582 [0.571 to 0.587] | 0.579 [0.571 to 0.621] | 1.01× | 1.036 [1.032 to 1.050] | 0.561× |
| `build/32` | 1.273 [1.267 to 1.291] | 1.175 [1.149 to 1.264] | 1.08× | 2.043 [2.004 to 2.765] | 0.623× |
| `build/1000` | 33.742 [33.692 to 33.869] | 14.103 [14.061 to 14.247] | 2.39× | 29.486 [29.426 to 29.553] | 1.144× |
| `median/1000` | 0.114 [0.111 to 0.115] | 0.168 [0.165 to 0.186] | 0.68× | 0.776 [0.772 to 0.788] | 0.147× |
| `quantile_99/1000` | 0.194 [0.184 to 0.202] | 0.224 [0.219 to 0.264] | 0.87× | 1.531 [1.529 to 1.534] | 0.127× |
| `build/10000` | 480.405 [480.159 to 492.154] | 167.540 [166.778 to 171.302] | 2.87× | 797.142 [795.979 to 803.314] | 0.603× |
| `build/100000` | 7342.468 [7244.117 to 10008.371] | 2382.743 [2364.492 to 2401.388] | 3.08× | 3519.696 [3500.510 to 4720.224] | 2.086× |
| `build/1000000` | 119488.746 [112022.763 to 121789.325] | 30519.509 [30094.684 to 38599.854] | 3.92× | 30914.588 [30599.538 to 31337.159] | 3.865× |
| `median/1000000` | 0.118 [0.115 to 0.127] | 0.209 [0.203 to 0.211] | 0.56× | 0.257 [0.250 to 0.271] | 0.459× |
| `quantile_99/1000000` | 0.173 [0.172 to 0.181] | 0.249 [0.242 to 0.329] | 0.69× | 0.366 [0.358 to 0.377] | 0.472× |
| `merge_sequential_40/32` | 128.025 [127.230 to 128.903] | 135.925 [134.435 to 136.730] | 0.94× | 2654.452 [2644.560 to 2678.889] | 0.048× |
| `merge_sequential_40/1000` | 259.444 [257.869 to 271.897] | 274.450 [273.366 to 275.372] | 0.95× | 18969.529 [18946.065 to 19001.929] | 0.014× |
| `merge_sequential_40/10000` | 305.528 [303.701 to 309.292] | 323.613 [322.516 to 324.428] | 0.94× | 19218.224 [19173.831 to 19364.388] | 0.016× |
| `build/0` | No equivalent | N/A | N/A | 0.933 [0.928 to 1.357] | N/A |
| `cdf_zero/1000` | No equivalent | N/A | N/A | 2.125 [2.124 to 2.128] | N/A |
| `cdf_zero/1000000` | No equivalent | N/A | N/A | 2.195 [2.193 to 2.198] | N/A |
| `merge_all_40/32` | No equivalent | N/A | N/A | 2646.344 [2642.878 to 2667.881] | N/A |
| `merge_all_40/1000` | No equivalent | N/A | N/A | 18992.021 [18942.598 to 19070.668] | N/A |
| `merge_all_40/10000` | No equivalent | N/A | N/A | 19204.669 [19193.217 to 19313.392] | N/A |

## Storage and accuracy controls

Logical centroid bytes count mean + weight + kind fields only: legacy 8/12 bytes, modern 13/17 bytes per centroid for f32/f64. This excludes struct padding, allocation capacity, headers, Python objects and cached arrays; it is not process RSS. Rank error is the maximum distance from the empirical rank interval at q=0.01, 0.5, 0.99 for this workload only. It does not replace the full accuracy suite.

| Workload | Precision | Legacy centroids / logical bytes / rank error | Modern centroids / logical bytes / rank error |
| --- | --- | --- | --- |
| `build/1000000` | f32 | 146 / 1,168 / 0.000071 | 1000 / 13,000 / 0.000021 |
| `build/1000000` | f64 | 146 / 1,752 / 0.000071 | 1000 / 17,000 / 0.000020 |
| `merge_sequential_40/1000` | f32 | 278 / 2,224 / 0.000100 | 1000 / 13,000 / 0.000025 |
| `merge_sequential_40/1000` | f64 | 278 / 3,336 / 0.000100 | 1000 / 17,000 / 0.000025 |

Legacy has no CDF API; the modern CDF timings therefore have no baseline ratio. The benchmark does not cover concurrent throughput, all distributions, equal memory tuning, allocator/RSS behavior or every query tail. See the [validation record](validation.md) and [known statistical limits](../../tests/quality/ACCURACY.md).
