# API behavior

The Rust library supplies compression and queries for Python, Polars, Java and the CLI. The Python constructor selects one of two calling conventions. See the [upgrade guide](ROLLOUT.md) for examples and all seven differences covered by the original Python suite.

## Python construction

`TDigest.from_array(values)` uses the original default of `delta=300`. The delta API accepts Float32 and Float64 NumPy arrays, skips NaNs and retains infinite endpoints. Merge and update return new digests. The total weight must fit in a uint32. Pickles from 0.1.0 provide centroid means and weights for reconstruction. The shared core supplies the numerical results. For example, the 10th percentile of `[1.0, 2.0]` changes from 0.7 to 1.0.

Pass `max_size=` for capacity mode. It accepts finite observations, positive finite weights, CDF queries and updates in place. Python accepts capacities from 10 to 20,000. Rust permits any positive capacity. The default capacity for the underlying engine and Polars is 1,000. Supply one sizing parameter per Python constructor. The [Python object guide](bindings/python/OBJECT_API.md) documents return types, precision and ownership for each mode.

The capacity constructors copy inputs into owned Rust vectors. Contiguous, aligned NumPy arrays of native Float32 or Float64 use a bulk copy. Other supported layouts follow the generic conversion path. Once conversion finishes, independent constructors can run concurrently with the GIL released.

## State, queries and updates

A centroid stores its mean in the selected precision and its mass in Float64. The digest also keeps the observed extrema, weighted sum, total mass, compression settings and centroid kinds. Rust builders and state decoders validate those fields before exposing a digest. The stored weighted sum may retain information lost when centroid means were rounded. Validation allows for that rounding and rejects contradictory mass or extrema.

Weighted observations must have finite values and strictly positive finite weights. Float32 conversion rejects overflow and a nonzero value rounding to zero. Training rejects unrepresentable products of mixed observations. For a single exact point, the mean and quantiles can still equal the observed value when the rounded weighted sum is zero. Adding an empty batch preserves the digest.

A capacity quantile takes a finite probability in `[0, 1]`. Python, Java, Polars and the CLI reject invalid probabilities. The raw Rust method clamps probabilities to the interval and propagates NaN. The median uses the weighted 0.5 quantile. An empty quantile or median yields NaN in Rust, Python capacity mode and Java. Polars returns null.

The CDF assigns a tied value the mass below it plus half the tied mass, divided by total mass. On nonempty input, probes below the observed minimum yield zero and probes above the maximum yield one. NaN probes and empty digests yield NaN. Python scalar probes return floats, lists and tuples retain their container, and NumPy vectors return independent Float64 arrays. Multidimensional query arrays must be flattened explicitly.

Capacity merges require matching precision, capacity, scale, singleton policy and delta, including for empty inputs. Cast precision explicitly when needed. An empty `merge_all` produces a Float64 digest with capacity 1,000, K2 scale and the default singleton policy. A failed update, iterable merge or rescaling leaves the receiver intact. Weight scaling changes the total mass and sum. Value scaling changes the means, extrema and sum. Both require a positive finite factor.

## Polars

Build digests inside a lazy aggregation with `td.tdigest`. A Float32 input column produces Float32 means. Other numeric columns produce Float64 means. Quantile results follow the stored mean precision, and scalar or list CDF results follow the probe dtype as described in the [Polars guide](bindings/python/POLARS_API.md).

CDF broadcasts one digest to a column of probes, one scalar probe to a column of digests, or evaluates corresponding rows when the column lengths match. An aligned empty digest produces its own NaN. A null digest, null training value or null probe is an error. A list of probes in a row returns a list of probabilities.

`from_bytes` reduces each logical group to one digest. Supply an explicit storage precision so Polars can plan the schema. For eager binary data, `infer_column_precision` can determine the hint. Each blob must match that hint. An empty group returns one empty state. A null or malformed blob raises an error.

## Serialization

TDIG v3 stores mean precision, Float64 weights, centroid kinds, raw statistics and configuration. Python capacity pickles and copies preserve this state. The Polars struct codec also reads older structs that omit configuration or use Float32 weights.

TDIG v1 requires positive integer weights with a total that fits in a u64. It infers kind from weight, which can change the interpretation of a weighted centroid. V2 stores weights and kinds explicitly. Delta, edge pin counts above 255, and Float32 means paired with weights that require Float64 precision need v3 for export. Older formats do not identify the mean precision of an empty payload. V3 stores it in the header. The [wire format description](tdigest_design.md) gives the layout and checksum rules.

Core construction and updates return `Result`. Python reports `ValueError` or `TypeError`, Polars reports expression errors and Java reports invalid arguments or native state errors. The Java API supports independent handles. A caller sharing a mutable handle across threads must coordinate access.

## Building and measuring

The Python package supports standard CPython 3.10 through 3.15. Numerical use requires NumPy. The optional Polars dependency is loaded when an expression needs it. The Java API targets Java 11 bytecode. The repository includes Scala, Kotlin and Spark examples. The Java guide covers native loading, supported JDKs and offline builds. [Python package](bindings/python/PYTHON_README.md) · [Java binding](bindings/java/README.md)

`make test` includes the fast accuracy matrix. `make quality-extended` exercises more capacities, merge orders and datasets. Both compare quantiles and CDF results with independently sorted observations. The benchmark report identifies the wheels, workloads and settings used for the published comparisons. [Accuracy measurements](tests/quality/README.md) · [Performance and accuracy](docs/upstream-1.0.0/comparison.md)
