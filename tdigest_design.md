# How the Rust digest works

A digest summarizes a distribution as a sequence of centroids ordered by mean. Each centroid stores a mean, a weight and a kind. An atomic centroid represents observations at exactly one value. A mixed centroid summarizes observations at different values. Queries use that distinction to preserve the rank of a repeated observation.

## Storage and arithmetic

Means and observed extrema use the chosen precision, Float32 or Float64. Centroid weights, total mass and the sum of the weighted observations use Float64 in both cases. A Float32 weight of 2²⁴ cannot distinguish one additional observation. Keeping the weight in Float64 preserves that increment and the rank boundary it can move.

The digest retains the sum from its inputs. Reconstructing it from compressed means would throw away information, especially after rounding to Float32. Cluster averaging uses compensated arithmetic for cancellation and intermediate overflow. An atomic point retains its value even when its weighted moment rounds to zero. A later merge or scaling operation can recover a representable moment from the point and its mass. A mixed centroid cannot recover that information.

## Building and merging

The builder checks its configuration and the consistency of supplied state. Unsorted inputs are sorted before merging. An ordered stream of observations can be merged with the existing centroids directly. To merge several digests, a heap draws the next centroid from each sorted input. Centroids with equal means are combined before compression. Total weight, the sum and the observed extrema come from the contributing digests.

Merges check every contributor, including an empty digest. Capacity, scale, singleton policy, delta and precision must agree. A caller can cast precision explicitly. Distinct means that collapse to one value in the cast retain their mass as a mixed centroid. Mutating operations prepare and validate the result before replacing the receiver, so a failed merge or scale leaves its previous state available.

## Compression

The scale function maps rank to a coordinate called `k`. The compressor walks the ordered centroids and combines neighbours while the change in `k` across the proposed cluster stays within its limit. A steep scale near the tails allows less mass in those clusters. The available families are K1, K2, K2Norm, K3 and Quad.

Capacity mode defaults to K2. If the first pass produces too many interior centroids, the compressor searches for a smaller scale parameter. Trial passes count clusters. Only the chosen pass needs to build their means. With K2 and integral weights totaling less than 2⁵³, the search can reuse the log odds at each rank boundary. If the scale search still exceeds capacity, an ordered grouping by weight absorbs the remaining mass.

The singleton policy determines how much space is available for the interior.

| Policy | How capacity applies |
| --- | --- |
| `Off` | All centroids share the configured capacity. |
| `Use` | When capacity allows room for an interior, the compressor reserves the two endpoints within the total capacity. At capacities one and two, all observations participate in compression. |
| `UseWithProtectedEdges(k)` | The compressor reserves up to `k` atomic centroids at each edge. The configured capacity applies to the interior, so the final count can exceed it. |

Delta mode uses K2Norm with singleton protection off. It skips the capacity search. The scale normalizer is `4 * ln(n / delta) + 24`, where `n` is the number of centroids entering the pass. Rank still depends on their cumulative weights. A nonpositive normalizer would reverse the scale, so this pass retains its input centroids. Specifying the same delta on two workloads need not produce the same count.

## Quantile, median and CDF

A CDF query asks what fraction of the mass lies below a value, counting half the mass tied at that value. The implementation builds a cumulative weight array once per batch and uses a binary search on the means for each probe. Between two atomic centroids the rank is constant. For example, with equally weighted observations at 10 and 20, the rank is 0.25 at 10, 0.5 anywhere strictly between them, and 0.75 at 20. Where a neighbouring centroid is mixed, interpolation distributes its share of the mass across the interval.

Quantile looks up a value at a given rank. Inside the mass of an atomic observation, it returns that observation. It interpolates across the remaining span between neighbouring centroids. The observed minimum and maximum define the endpoints. Median uses the same weighted query at 0.5. Raw Rust quantile clamps finite probabilities to the unit interval. The strict binding entry points validate probabilities. The [API guide](api_design.md) describes the behavior of each binding.

When the total mass is positive and subnormal, halving a weight can erase its contribution. The query scales a temporary view by two powers of two, bringing the total into `[1, 2)` while keeping both factors representable. Stored weights stay intact. This special case applies to a subnormal total. With a normal total, an extremely small component can still lose precision at a rank boundary.

## Transferring state

TDIG is the binary format shared by the bindings. All versions use little endian fields. Writers default to v3. The [wire implementation](src/tdigest/wire.rs) lists the byte offsets and extension flags.

| Version | Representation |
| --- | --- |
| v1 | Integer weights. The reader infers centroid kind from the weight. Payload length determines mean precision for a nonempty digest. |
| v2 | Float64 weights and an explicit kind per centroid. Payload length still identifies precision for a nonempty digest. |
| v3 | The header identifies precision and can carry a checksum, a delta and a wider protected edge count. A flag identifies Float32 means paired with weights that require Float64 precision. |

Explicit export to an older format checks what that version can represent. Use v3 to preserve the full state. Polars structs also carry the compression settings, centroid kinds and weights. The decoder accepts the original six field schema with its historical defaults. Reading TDIG into a Polars expression requires an explicit precision so Polars can plan the result schema before reading any rows.

Reconstruction checks ordered finite means, positive weights, extrema and aggregate consistency. Empty state has zero totals and NaN extrema. The mass check allows for accumulation error, and the aggregate mean check allows for rounding in compressed means. The original weighted sum remains part of the digest.

## Checking the estimates

The [accuracy report](tests/quality/ACCURACY.md) compares queries with sorted observations, including ties, weighted data and merges of 40 digests. The [comparison with 0.1.0](docs/upstream-1.0.0/comparison.md) includes measurements on recorded data, the original Python benchmark and timing runs where both builds produced identical centroid means and weights.
