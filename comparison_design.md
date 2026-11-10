# Historical engine comparison

The release now exposes delta and capacity modes from one Rust engine. See [Python compatibility](compat/python-modes.md) for current behavior.

## Modern versus original GR: measured accuracy (CI, 21 October 2026)

At comparable logical centroid storage, modern had lower average rank error in
279 of 324 recorded real-data cases. Legacy had lower grouped peak value error
on Energy and won several synthetic distributions. The historical report gives
the selection rule, per-workload ratios and the limits of those measurements.
[Recorded results](compat/quality-20261020/RESULTS.md)

The default-setting accuracy study answers a different question. Capacity
1,000 and legacy delta 300 retain different numbers of centroids. Consult the
[default-setting results](tests/quality/ACCURACY.md) and [performance measurements](docs/upstream-1.0.0/performance.md)
for merge cost, query cost and storage.

Algorithm references include the [t-digest paper](https://arxiv.org/abs/1902.04023)
and [reference implementation](https://github.com/tdunning/t-digest).
