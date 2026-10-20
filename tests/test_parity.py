"""Check Spark outputs match the legacy answer key.

data/processed/norman/{legacy,spark}/ -> line up rows per table -> counts, values, rankings
"""

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).parents[1] / "data/processed/norman"
TOL = 1e-9  # max absolute gap; Spark adds in a different order
TOP_RANKS = 10  # gene ranks that must match exactly

pytestmark = pytest.mark.skipif(not (ROOT / "spark").exists(), reason="run both pipelines first")


def matched(table: str, keys: list[str]) -> pd.DataFrame:
    """Line up one table's legacy and Spark rows; fail on duplicate or one-sided rows.

    In: table name, key columns.
    Out: merged rows; shared columns suffixed _legacy / _spark.
    """
    legacy = pd.read_parquet(ROOT / "legacy" / f"{table}.parquet")
    spark = pd.read_parquet(ROOT / "spark" / table)
    assert not legacy.duplicated(keys).any(), f"legacy {table}: duplicate rows"
    assert not spark.duplicated(keys).any(), f"spark {table}: duplicate rows"
    m = legacy.merge(spark, on=keys, how="outer", suffixes=("_legacy", "_spark"), indicator=True)
    missing = m[m["_merge"] != "both"]
    assert missing.empty, f"{table}: {len(missing)} rows on one side only\n{missing.head()}"
    return m


def gap(m: pd.DataFrame, col: str) -> float:
    """Largest absolute difference between legacy and Spark values of one column.

    In: merged rows, column name without suffix.
    Out: max gap.
    """
    return (m[f"{col}_legacy"] - m[f"{col}_spark"]).abs().max()


def test_perturbations():
    m = matched("perturbations", ["name"])
    assert (m["cell_count_legacy"] == m["cell_count_spark"]).all()
    assert all(list(a) == list(b) for a, b in zip(m["target_genes_legacy"], m["target_genes_spark"]))


def test_signatures():
    m = matched("signatures", ["perturbation", "gene"])
    assert gap(m, "change") <= TOL


def test_top_genes():
    m = matched("top_genes", ["perturbation", "rank"])
    top = m[m["rank"] <= TOP_RANKS]
    assert (top["gene_legacy"] == top["gene_spark"]).all()
    assert gap(top, "change") <= TOL


def test_euclidean():
    m = matched("euclidean", ["a", "b"])
    assert gap(m, "distance") <= TOL


def test_similar_euclidean():
    m = matched("similar_euclidean", ["perturbation", "rank"])
    assert (m["neighbor_legacy"] == m["neighbor_spark"]).all()
    assert gap(m, "distance") <= TOL
