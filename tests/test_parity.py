"""Check Spark outputs match the legacy answer key.

tests/fixtures/tiny/ -> run legacy + Spark into temp folder -> line up rows per table
data/processed/norman/{legacy,spark}/ (if present) -> same checks
"""

from pathlib import Path

import pandas as pd
import pytest

from pipeline import legacy_signatures, spark_signatures

FIXTURE = Path(__file__).parent / "fixtures/tiny"
NORMAN = Path(__file__).parents[1] / "data/processed/norman"
CONTROL = "control"
TOL = 1e-9  # max absolute gap; Spark adds in a different order
TOP_RANKS = 10  # gene ranks that must match exactly


@pytest.fixture(scope="session")
def tiny(tmp_path_factory) -> Path:
    """Run both pipelines on the committed fixture.

    In: pytest temp folder factory.
    Out: folder holding legacy/ and spark/ outputs.
    State: starts and stops Spark once per test session.
    """
    out = tmp_path_factory.mktemp("tiny")
    legacy_signatures.run(FIXTURE, out / "legacy", CONTROL)
    spark_signatures.run(FIXTURE, out / "spark", CONTROL)
    return out


@pytest.fixture(params=["tiny", "norman"])
def root(request) -> Path:
    """Yield each dataset's output folder; skip Norman when its outputs are missing.

    In: dataset parameter.
    Out: folder holding legacy/ and spark/ outputs.
    """
    if request.param == "tiny":
        return request.getfixturevalue("tiny")
    if not (NORMAN / "spark").exists():
        pytest.skip("Norman outputs missing; run both pipelines first")
    return NORMAN


def matched(root: Path, table: str, keys: list[str]) -> pd.DataFrame:
    """Line up one table's legacy and Spark rows; fail on duplicate or one-sided rows.

    In: output folder, table name, key columns.
    Out: merged rows; shared columns suffixed _legacy / _spark.
    """
    legacy = pd.read_parquet(root / "legacy" / f"{table}.parquet")
    spark = pd.read_parquet(root / "spark" / table)
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


def test_perturbations(root):
    m = matched(root, "perturbations", ["name"])
    assert (m["cell_count_legacy"] == m["cell_count_spark"]).all()
    assert all(list(a) == list(b) for a, b in zip(m["target_genes_legacy"], m["target_genes_spark"]))


def test_signatures(root):
    m = matched(root, "signatures", ["perturbation", "gene"])
    assert gap(m, "change") <= TOL


def test_top_genes(root):
    m = matched(root, "top_genes", ["perturbation", "rank"])
    top = m[m["rank"] <= TOP_RANKS]
    assert (top["gene_legacy"] == top["gene_spark"]).all()
    assert gap(top, "change") <= TOL


def test_euclidean(root):
    m = matched(root, "euclidean", ["a", "b"])
    assert gap(m, "distance") <= TOL


def test_similar_euclidean(root):
    m = matched(root, "similar_euclidean", ["perturbation", "rank"])
    assert (m["neighbor_legacy"] == m["neighbor_spark"]).all()
    assert gap(m, "distance") <= TOL
