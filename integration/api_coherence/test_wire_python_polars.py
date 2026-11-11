from __future__ import annotations


class TestPythonRoundTripSerde:
    def test_python_round_trip(
        self, dataset, expect, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td

        kwargs = dict(
            max_size=cfg["max_size"],
            scale=cfg["scale_py"],
            singleton_policy=cfg["singleton_py"],
            precision=cfg["precision_py"],
        )
        if cfg.get("singleton_py") == "edges" and cfg.get("pin_per_side") is not None:
            kwargs = add_pin_kw_fn(kwargs)

        d1 = td.TDigest.from_array(dataset["DATA"], **kwargs)

        blob = d1.to_bytes()
        assert isinstance(blob, (bytes, bytearray))

        d2 = td.TDigest.from_bytes(bytes(blob))

        q1 = d1.quantile(expect["P"])
        q2 = d2.quantile(expect["P"])
        c1 = d1.cdf(expect["X"])
        c2 = d2.cdf(expect["X"])

        assert_close_fn(q2, q1, expect["EPS"])
        assert_close_fn(c2, c1, expect["EPS"])
        assert_close_fn(q2, expect["Q50"], expect["EPS"])
        assert_close_fn(c2, expect["CDF2"], expect["EPS"])


class TestPythonPolarsSerdeInterop:
    @staticmethod
    def _build_python_digest(dataset, cfg, add_pin_kw_fn, precision: str):
        """
        Build a Python TDigest with explicit precision ("f32" or "f64").
        """
        import tdigest_rs as td

        py_kwargs = dict(
            max_size=cfg["max_size"],
            scale=cfg["scale_py"],
            singleton_policy=cfg["singleton_py"],
            precision=precision,
        )
        if cfg.get("singleton_py") == "edges" and cfg.get("pin_per_side") is not None:
            py_kwargs = add_pin_kw_fn(py_kwargs)

        d = td.TDigest.from_array(dataset["DATA"], **py_kwargs)
        assert d.inner_kind() == precision
        return d

    @staticmethod
    def _build_polars_digest(dataset, cfg, add_pin_kw_fn, precision: str, float_dtype):
        """
        Build a Polars TDigest struct column over a single Float32/Float64 column.
        """
        import tdigest_rs as td
        import polars as pl

        df = pl.DataFrame({"x": dataset["DATA"]}).with_columns(
            pl.col("x").cast(float_dtype)
        )
        assert df.schema["x"] == float_dtype

        td_kwargs = dict(
            max_size=cfg["max_size"],
            scale=cfg["scale_pl"],
            singleton_policy=cfg["singleton_pl"],
            precision=precision,
        )
        if cfg.get("singleton_pl") == "edges" and cfg.get("pin_per_side") is not None:
            td_kwargs = add_pin_kw_fn(td_kwargs)

        df_td = df.with_columns(td_col=td.tdigest("x", **td_kwargs))
        assert "td_col" in df_td.schema
        return df_td

    @staticmethod
    def _assert_polars_digest_dtype(td_dtype, pl, expect_f32: bool):
        """
        Check struct schema:
        - compact (f32) → min/max are Float32
        - full   (f64) → min/max are Float64
        """
        # Polars dtypes don't have `.is_struct()`; we just rely on `.fields`.
        fields = getattr(td_dtype, "fields", None)
        assert fields is not None, f"expected Struct dtype, got {td_dtype!r}"

        min_field = next(f for f in fields if f.name == "min")
        max_field = next(f for f in fields if f.name == "max")

        if expect_f32:
            assert min_field.dtype == pl.Float32
            assert max_field.dtype == pl.Float32
        else:
            assert min_field.dtype == pl.Float64
            assert max_field.dtype == pl.Float64

    def test_python_f32_to_polars_f32(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        d_py = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f32")
        blob = d_py.to_bytes()
        assert isinstance(blob, (bytes, bytearray, memoryview))

        df = pl.DataFrame({"blob": [blob]})
        df2 = df.with_columns(td_col=td.from_bytes("blob", precision="f32"))
        assert df2.height == 1

        td_dtype = df2.schema["td_col"]
        self._assert_polars_digest_dtype(td_dtype, pl, expect_f32=True)

        # Quantile / CDF coherence.
        x0 = float(dataset["DATA"][0])
        out = df2.select(
            q=td.quantile("td_col", 0.5),
            c=td.cdf("td_col", pl.lit(x0, dtype=pl.Float64)),
        )
        q_pl = float(out["q"][0])
        c_pl = float(out["c"][0])

        assert_close_fn(q_pl, d_py.quantile(0.5), 1e-9)
        assert_close_fn(c_pl, d_py.cdf(x0), 1e-9)

    def test_python_f64_to_polars_f64(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        d_py = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f64")
        blob = d_py.to_bytes()

        df = pl.DataFrame({"blob": [blob]})
        df2 = df.with_columns(td_col=td.from_bytes("blob", precision="f64"))

        td_dtype = df2.schema["td_col"]
        self._assert_polars_digest_dtype(td_dtype, pl, expect_f32=False)

        x0 = float(dataset["DATA"][0])
        out = df2.select(
            q=td.quantile("td_col", 0.5),
            c=td.cdf("td_col", pl.lit(x0, dtype=pl.Float64)),
        )
        q_pl = float(out["q"][0])
        c_pl = float(out["c"][0])

        assert_close_fn(q_pl, d_py.quantile(0.5), 1e-9)
        assert_close_fn(c_pl, d_py.cdf(x0), 1e-9)

    def test_polars_f32_to_python_f32(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        df_td = self._build_polars_digest(
            dataset, cfg, add_pin_kw_fn, precision="f32", float_dtype=pl.Float32
        )

        # Schema check on Polars side.
        td_dtype = df_td.schema["td_col"]
        self._assert_polars_digest_dtype(td_dtype, pl, expect_f32=True)

        x0 = float(dataset["DATA"][0])
        out_pl = df_td.select(
            q=td.quantile("td_col", 0.5),
            c=td.cdf("td_col", pl.lit(x0, dtype=pl.Float64)),
        )
        q_pl = float(out_pl["q"][0])
        c_pl = float(out_pl["c"][0])

        blob = df_td.with_columns(blob=td.to_bytes("td_col")).select("blob").row(0)[0]

        d_py = td.TDigest.from_bytes(blob)
        assert isinstance(d_py, td.TDigest)
        assert d_py.inner_kind() == "f32"

        q_py = d_py.quantile(0.5)
        c_py = d_py.cdf(x0)

        assert_close_fn(q_py, q_pl, 1e-9)
        assert_close_fn(c_py, c_pl, 1e-9)

    def test_polars_f64_to_python_f64(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        df_td = self._build_polars_digest(
            dataset, cfg, add_pin_kw_fn, precision="f64", float_dtype=pl.Float64
        )

        td_dtype = df_td.schema["td_col"]
        self._assert_polars_digest_dtype(td_dtype, pl, expect_f32=False)

        x0 = float(dataset["DATA"][0])
        out_pl = df_td.select(
            q=td.quantile("td_col", 0.5),
            c=td.cdf("td_col", pl.lit(x0, dtype=pl.Float64)),
        )
        q_pl = float(out_pl["q"][0])
        c_pl = float(out_pl["c"][0])

        blob = df_td.with_columns(blob=td.to_bytes("td_col")).select("blob").row(0)[0]

        d_py = td.TDigest.from_bytes(blob)
        assert isinstance(d_py, td.TDigest)
        assert d_py.inner_kind() == "f64"

        q_py = d_py.quantile(0.5)
        c_py = d_py.cdf(x0)

        assert_close_fn(q_py, q_pl, 1e-9)
        assert_close_fn(c_py, c_pl, 1e-9)

    def test_python_f32_to_python_f32_via_polars(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        d_py = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f32")
        blob = d_py.to_bytes()

        df = pl.DataFrame({"blob": [blob]})
        df2 = df.with_columns(td_col=td.from_bytes("blob", precision="f32"))

        td_dtype = df2.schema["td_col"]
        self._assert_polars_digest_dtype(td_dtype, pl, expect_f32=True)

        blob2 = df2.with_columns(blob=td.to_bytes("td_col")).select("blob").row(0)[0]
        d_py2 = td.TDigest.from_bytes(blob2)

        assert isinstance(d_py2, td.TDigest)
        assert d_py2.inner_kind() == "f32"

        x0 = float(dataset["DATA"][0])
        assert_close_fn(d_py2.quantile(0.5), d_py.quantile(0.5), 1e-9)
        assert_close_fn(d_py2.cdf(x0), d_py.cdf(x0), 1e-9)

    def test_python_f64_to_python_f64_via_polars(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        d_py = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f64")
        blob = d_py.to_bytes()

        df = pl.DataFrame({"blob": [blob]})
        df2 = df.with_columns(td_col=td.from_bytes("blob", precision="f64"))

        td_dtype = df2.schema["td_col"]
        self._assert_polars_digest_dtype(td_dtype, pl, expect_f32=False)

        blob2 = df2.with_columns(blob=td.to_bytes("td_col")).select("blob").row(0)[0]
        d_py2 = td.TDigest.from_bytes(blob2)

        assert isinstance(d_py2, td.TDigest)
        assert d_py2.inner_kind() == "f64"

        x0 = float(dataset["DATA"][0])
        assert_close_fn(d_py2.quantile(0.5), d_py.quantile(0.5), 1e-9)
        assert_close_fn(d_py2.cdf(x0), d_py.cdf(x0), 1e-9)

    def test_polars_f32_to_polars_f32_via_python(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        df_td = self._build_polars_digest(
            dataset, cfg, add_pin_kw_fn, precision="f32", float_dtype=pl.Float32
        )

        td_dtype_orig = df_td.schema["td_col"]
        self._assert_polars_digest_dtype(td_dtype_orig, pl, expect_f32=True)

        x0 = float(dataset["DATA"][0])
        out_orig = df_td.select(
            q=td.quantile("td_col", 0.5),
            c=td.cdf("td_col", pl.lit(x0, dtype=pl.Float64)),
        )
        q_orig = float(out_orig["q"][0])
        c_orig = float(out_orig["c"][0])

        blob = df_td.with_columns(blob=td.to_bytes("td_col")).select("blob").row(0)[0]
        d_py = td.TDigest.from_bytes(blob)
        assert d_py.inner_kind() == "f32"

        blob2 = d_py.to_bytes()
        df2 = pl.DataFrame({"blob": [blob2]}).with_columns(td_rt=td.from_bytes("blob", precision="f32"))

        td_dtype_rt = df2.schema["td_rt"]
        self._assert_polars_digest_dtype(td_dtype_rt, pl, expect_f32=True)

        out_rt = df2.select(
            q=td.quantile("td_rt", 0.5),
            c=td.cdf("td_rt", pl.lit(x0, dtype=pl.Float64)),
        )
        q_rt = float(out_rt["q"][0])
        c_rt = float(out_rt["c"][0])

        assert_close_fn(q_rt, q_orig, 1e-9)
        assert_close_fn(c_rt, c_orig, 1e-9)

    def test_polars_f64_to_polars_f64_via_python(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        df_td = self._build_polars_digest(
            dataset, cfg, add_pin_kw_fn, precision="f64", float_dtype=pl.Float64
        )

        td_dtype_orig = df_td.schema["td_col"]
        self._assert_polars_digest_dtype(td_dtype_orig, pl, expect_f32=False)

        x0 = float(dataset["DATA"][0])
        out_orig = df_td.select(
            q=td.quantile("td_col", 0.5),
            c=td.cdf("td_col", pl.lit(x0, dtype=pl.Float64)),
        )
        q_orig = float(out_orig["q"][0])
        c_orig = float(out_orig["c"][0])

        blob = df_td.with_columns(blob=td.to_bytes("td_col")).select("blob").row(0)[0]
        d_py = td.TDigest.from_bytes(blob)
        assert d_py.inner_kind() == "f64"

        blob2 = d_py.to_bytes()
        df2 = pl.DataFrame({"blob": [blob2]}).with_columns(td_rt=td.from_bytes("blob", precision="f64"))

        td_dtype_rt = df2.schema["td_rt"]
        self._assert_polars_digest_dtype(td_dtype_rt, pl, expect_f32=False)

        out_rt = df2.select(
            q=td.quantile("td_rt", 0.5),
            c=td.cdf("td_rt", pl.lit(x0, dtype=pl.Float64)),
        )
        q_rt = float(out_rt["q"][0])
        c_rt = float(out_rt["c"][0])

        assert_close_fn(q_rt, q_orig, 1e-9)
        assert_close_fn(c_rt, c_orig, 1e-9)

    def test_infer_column_precision_mixed_raises(self, dataset, cfg, add_pin_kw_fn):
        import tdigest_rs as td
        import polars as pl
        import pytest

        d32 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f32")
        d64 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f64")

        blob32 = d32.to_bytes()
        blob64 = d64.to_bytes()

        df = pl.DataFrame({"blob": [blob32, blob64]})

        with pytest.raises(ValueError, match="Mixed TDIG wire precisions"):
            td.infer_column_precision(df, "blob", strict=True)

        prec = td.infer_column_precision(df, "blob", strict=False)
        assert prec == "f64"

    def test_infer_column_precision_all_f32(self, dataset, cfg, add_pin_kw_fn):
        import tdigest_rs as td
        import polars as pl

        d32 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f32")
        blob32 = d32.to_bytes()

        df = pl.DataFrame({"blob": [blob32, blob32]})

        prec_strict = td.infer_column_precision(df, "blob", strict=True)
        prec_relaxed = td.infer_column_precision(df, "blob", strict=False)

        assert prec_strict == "f32"
        assert prec_relaxed == "f32"

    def test_infer_column_precision_all_f64(self, dataset, cfg, add_pin_kw_fn):
        import tdigest_rs as td
        import polars as pl

        d64 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f64")
        blob64 = d64.to_bytes()

        df = pl.DataFrame({"blob": [blob64, blob64]})

        prec_strict = td.infer_column_precision(df, "blob", strict=True)
        prec_relaxed = td.infer_column_precision(df, "blob", strict=False)

        assert prec_strict == "f64"
        assert prec_relaxed == "f64"

    def test_infer_column_precision_all_nulls_defaults_f64(self):
        import tdigest_rs as td
        import polars as pl

        df = pl.DataFrame({"blob": [None, None]}).with_columns(
            pl.col("blob").cast(pl.Binary)
        )
        prec = td.infer_column_precision(df, "blob", strict=True)
        assert prec == "f64"

    def test_from_bytes_explicit_mixed_column_raises(self, dataset, cfg, add_pin_kw_fn):
        import tdigest_rs as td
        import polars as pl
        import pytest

        d32 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f32")
        d64 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f64")

        blob32 = d32.to_bytes()
        blob64 = d64.to_bytes()

        df = pl.DataFrame({"blob": [blob32, blob64]})

        with pytest.raises(
            pl.exceptions.ComputeError, match="mixed f32/f64 blobs in column"
        ):
            df.with_columns(td_col=td.from_bytes("blob", precision="f64"))

    def test_from_bytes_with_precision_f32_on_f64_blobs_raises(
        self, dataset, cfg, add_pin_kw_fn
    ):
        import tdigest_rs as td
        import polars as pl
        import pytest

        d64 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f64")
        blob64 = d64.to_bytes()
        df = pl.DataFrame({"blob": [blob64]})

        with pytest.raises(
            pl.exceptions.ComputeError, match="mixed f32/f64 blobs in column"
        ):
            df.with_columns(td_col=td.from_bytes("blob", precision="f32"))

    def test_from_bytes_with_precision_f64_on_f32_blobs_raises(
        self, dataset, cfg, add_pin_kw_fn
    ):
        import tdigest_rs as td
        import polars as pl
        import pytest

        d32 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f32")
        blob32 = d32.to_bytes()
        df = pl.DataFrame({"blob": [blob32]})

        with pytest.raises(
            pl.exceptions.ComputeError, match="mixed f32/f64 blobs in column"
        ):
            df.with_columns(td_col=td.from_bytes("blob", precision="f64"))

    def test_from_bytes_with_any_null_blob_row_raises(
        self, dataset, cfg, add_pin_kw_fn
    ):
        import tdigest_rs as td
        import polars as pl
        import pytest

        d64 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f64")
        blob64 = d64.to_bytes()
        df = pl.DataFrame({"blob": [blob64, None]}).with_columns(
            pl.col("blob").cast(pl.Binary)
        )

        with pytest.raises(pl.exceptions.ComputeError, match="(?i)null"):
            df.with_columns(td_col=td.from_bytes("blob", precision="f64"))

    def test_from_bytes_all_null_blob_column_raises(self):
        import tdigest_rs as td
        import polars as pl
        import pytest

        df = pl.DataFrame({"blob": [None, None]}).with_columns(
            pl.col("blob").cast(pl.Binary)
        )

        with pytest.raises(pl.exceptions.ComputeError, match="(?i)null"):
            df.with_columns(td_col=td.from_bytes("blob", precision="f64"))

    def test_from_bytes_empty_blob_bytes_raises_decode_error(self):
        import tdigest_rs as td
        import polars as pl
        import pytest

        df = pl.DataFrame({"blob": [b""]})

        with pytest.raises(
            pl.exceptions.ComputeError, match="(?i)(tdig|decode|header|buffer)"
        ):
            df.with_columns(td_col=td.from_bytes("blob", precision="f64"))

    def test_from_bytes_with_precision_f32_homogeneous_column(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        d32 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f32")
        blob32 = d32.to_bytes()

        df = pl.DataFrame({"blob": [blob32]})
        df2 = df.with_columns(td_col=td.from_bytes("blob", precision="f32"))

        td_dtype = df2.schema["td_col"]
        self._assert_polars_digest_dtype(td_dtype, pl, expect_f32=True)

        x0 = float(dataset["DATA"][0])
        out = df2.select(
            q=td.quantile("td_col", 0.5),
            c=td.cdf("td_col", pl.lit(x0, dtype=pl.Float64)),
        )
        q_pl = float(out["q"][0])
        c_pl = float(out["c"][0])

        assert_close_fn(q_pl, d32.quantile(0.5), 1e-9)
        assert_close_fn(c_pl, d32.cdf(x0), 1e-9)

    def test_inferred_f32_hint_preserves_wire_precision(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        d32 = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f32")
        blob32 = d32.to_bytes()

        df = pl.DataFrame({"blob": [blob32]})

        df2 = df.with_columns(td_col=td.from_bytes("blob", precision=td.infer_column_precision(df, "blob")))

        td_dtype = df2.schema["td_col"]
        self._assert_polars_digest_dtype(td_dtype, pl, expect_f32=True)

        x0 = float(dataset["DATA"][0])
        out_pl = df2.select(
            q=td.quantile("td_col", 0.5),
            c=td.cdf("td_col", pl.lit(x0, dtype=pl.Float64)),
        )
        q_pl = float(out_pl["q"][0])
        c_pl = float(out_pl["c"][0])

        assert_close_fn(q_pl, d32.quantile(0.5), 1e-9)
        assert_close_fn(c_pl, d32.cdf(x0), 1e-9)

        blob_rt = df2.with_columns(blob=td.to_bytes("td_col")).select("blob").row(0)[0]
        d_rt = td.TDigest.from_bytes(blob_rt)
        assert d_rt.inner_kind() == "f32"

        q_rt = d_rt.quantile(0.5)
        c_rt = d_rt.cdf(x0)

        assert_close_fn(q_rt, d32.quantile(0.5), 1e-9)
        assert_close_fn(c_rt, d32.cdf(x0), 1e-9)

    def test_python_to_bytes_explicit_wire_versions_roundtrip(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td

        d = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f64")
        x0 = float(dataset["DATA"][0])

        for version in (1, 2, 3):
            blob = d.to_bytes(version=version)
            d_rt = td.TDigest.from_bytes(blob)
            assert d_rt.inner_kind() == "f64"
            assert_close_fn(d_rt.quantile(0.5), d.quantile(0.5), 1e-6)
            assert_close_fn(d_rt.cdf(x0), d.cdf(x0), 1e-6)

    def test_from_bytes_explicit_accepts_mixed_v1_v2_same_precision(
        self, dataset, cfg, add_pin_kw_fn, assert_close_fn
    ):
        import tdigest_rs as td
        import polars as pl

        d = self._build_python_digest(dataset, cfg, add_pin_kw_fn, precision="f64")
        blob_v1 = d.to_bytes(version=1)
        blob_v2 = d.to_bytes(version=2)

        df = pl.DataFrame({"blob": [blob_v1, blob_v2]})
        df2 = df.with_columns(td_col=td.from_bytes("blob", precision="f64"))

        out = df2.select(
            q=td.quantile("td_col", 0.5),
            c=td.cdf("td_col", pl.lit(float(dataset["DATA"][0]), dtype=pl.Float64)),
        )
        q = float(out["q"][0])
        c = float(out["c"][0])

        assert_close_fn(q, d.quantile(0.5), 1e-6)
        assert_close_fn(c, d.cdf(float(dataset["DATA"][0])), 1e-6)
