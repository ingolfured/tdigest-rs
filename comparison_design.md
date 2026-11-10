# Historical engine comparison

The [1.0 vs 0.1.0 wheel comparison](docs/upstream-1.0.0/comparison.md) measures both constructor modes on recorded data and reruns the original Python benchmark. The [upgrade guide](ROLLOUT.md) covers the existing Python API.

## Modern versus original GR: measured accuracy (CI, 21 October 2026)

At comparable logical centroid storage, modern had lower average rank error in
279 of 324 cases on recorded data. Legacy had lower grouped peak value error
on Energy and won several synthetic distributions. The historical report gives
the selection rule, ratios by workload and the limits of those measurements.
[Recorded results](compat/quality-20261020/RESULTS.md)

The accuracy study at default settings answers a different question. Capacity
1,000 and legacy delta 300 retain different numbers of centroids. Consult the
[results at default settings](tests/quality/ACCURACY.md) and [performance measurements](docs/upstream-1.0.0/performance.md)
for merge cost, query cost and storage.

Algorithm references include the [original paper](https://arxiv.org/abs/1902.04023)
and [reference implementation](https://github.com/tdunning/t-digest).
