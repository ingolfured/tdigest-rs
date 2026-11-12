# tdigest-rs

tdigest-rs is a Rust library for estimating quantiles and percentile ranks from compact, mergeable summaries of streaming data.

## Features

- ⚡ **Parallel CDF queries** rank large batches across CPU cores.
- 🎯 **Quantiles and trimmed means** report p99 or average the middle 90%.
- 🐻‍❄️ **Native Polars expressions** build, merge, and query digests by group.
- 🔀 **Add batches in place** or combine partitioned digests with a k-way merge.
- ⚖️ **Weighted samples** support fractional weights, counts, and rescaling.
- 🧊 **NumPy input** accepts Float16, Float32, and Float64 arrays.
- 🎚️ **Tune tail accuracy** with five scales, a size budget, and edge protection.
- 🗜️ **K2 compression** can reuse logarithms across integer-weight trials.
- 🧵 **Parallel Python builds** release the GIL during Rust construction.
- 📦 **Portable digests** move between Python, Polars, Rust, and Java.
- 🖥️ **CLI queries** run on saved digests built from text, CSV, JSON, or NDJSON.

## Install

To try 1.0 from a source checkout, run this from the repository root with Rust 1.95 and CPython 3.10–3.15:

```sh
python -m pip install './bindings/python[polars]'
```

For a published 1.x wheel, use `python -m pip install 'tdigest-rs[polars]>=1.0,<2'`. Omit `[polars]` for Python and NumPy alone.

## Python

These four requests took 10, 20, 30, and 80 ms. Ask for two percentiles, then turn a latency back into a rank:

```python
import numpy as np
from tdigest_rs import TDigest

latency_ms = np.array([10, 20, 30, 80], dtype=np.float16)
digest = TDigest.from_array(latency_ms, max_size=200, precision="f32")

print(digest.quantile([0.5, 0.99]))  # [25.0, 80.0]
print(digest.cdf([15, 25, 40]))      # [0.25, 0.5, 0.75]
```

If your input already contains counts, pass them as weights. Here nine requests took 12 ms and one took 80 ms. Combine two workers’ summaries to get a median across all twelve requests:

```python
from tdigest_rs import TDigest

east = TDigest.from_array([12, 80], weights=[9, 1], max_size=200)
west = TDigest.from_array([20, 30], max_size=200)
combined = TDigest.merge_all([east, west])
print(combined.count, combined.median())  # 12.0 12.0
```

## Polars

Keep one digest per service per hour. Merge the hourly digests to get each service’s p99 across the full period, all in one lazy query.

```python
import polars as pl
import tdigest_rs as td

requests = pl.LazyFrame({
    "service": ["search", "search", "search", "checkout", "checkout", "checkout"],
    "hour": [9, 9, 10, 9, 10, 10],
    "latency_ms": [12.0, 15.0, 48.0, 35.0, 80.0, 90.0],
})
hourly = requests.group_by("service", "hour").agg(
    td.tdigest("latency_ms", max_size=200).alias("digest")
)
by_service = hourly.group_by("service").agg(
    td.quantile(td.merge_tdigests("digest"), 0.99).alias("p99_ms")
)
print(by_service.sort("service").collect())  # checkout: 90 ms, search: 48 ms
```

## Rust

Keep a digest in a long-running process and add a batch whenever it arrives.

```rust
use tdigest_rs::{tdigest::TDigest, TdResult};

fn main() -> TdResult<()> {
    let mut digest = TDigest::<f64>::builder().max_size(200).build()?;
    digest.add_many(vec![12.0, 20.0, 48.0])?;
    digest.add(90.0)?;
    println!("{}", digest.quantile(0.5)); // 34
    Ok(())
}
```

## From the CLI to Java

Save a column of readings as a digest, then query the file:

```sh
cargo build --release --bin tdigest
printf 'value\n10\n20\n30\n' > numbers.csv
target/release/tdigest build --input numbers.csv --input-format csv --input-column value --to-digest readings.tdig
target/release/tdigest quantile --from-digest readings.tdig --p 0.5,0.99 --no-header
```

Open that same file in Java with the `com.gresearch.tdigest:tdigest-rs` JAR. The JAR bundles the native library for its target platform.

```java
import com.gresearch.tdigest.TDigest;
import java.nio.file.Files;
import java.nio.file.Path;

public class Example {
    public static void main(String[] args) throws Exception {
        byte[] bytes = Files.readAllBytes(Path.of("readings.tdig"));
        try (TDigest digest = TDigest.fromBytes(bytes)) {
            System.out.println(digest.median()); // 20.0
        }
    }
}
```

See the [JVM guide](bindings/java/README.md) for build instructions and Scala, Kotlin, and Spark examples.

## Development and release

From the repository root, run `make setup`, `make build`, and `make test`. Run `make lint` before contributing and include a changelog entry with each commit. See the [contributing guide](CONTRIBUTING.md), [code of conduct](CODE_OF_CONDUCT.md), [security policy](SECURITY.md), and [Apache 2.0 license](LICENSE).

## Legacy Python API

For the original Python calling convention, pass `delta=` with a Float32 or Float64 NumPy array. Omitting both sizing arguments selects `delta=300`. Here `update` and `merge` return a new digest:

```python
import numpy as np
from tdigest_rs import TDigest

first = TDigest.from_array(np.array([10, 20], dtype=np.float32), delta=300)
combined = first.update(np.array([30], dtype=np.float32))
print(first.median(), combined.median())  # 15.0 20.0
```

For numerical changes and pickle compatibility when upgrading, see the [1.0 release notes](RELEASE_NOTES_1.0.0.md).
