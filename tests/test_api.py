"""Check every API endpoint against the tiny fixture's Spark output, through real MongoDB.

tiny Spark output (conftest) -> pipeline.load_mongo -> disposable database minixell_test_<random>
  (+ decoy records under another dataset label) -> FastAPI app via TestClient -> responses
Expected values come straight from the Spark Parquet tables, not from loaded documents.
Needs MongoDB at MONGODB_URI and Java: `uv run --env-file .env pytest tests/test_api.py`.
"""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from api.main import DATASET, MAX_LIMIT, app
from pipeline import load_mongo

TOL = 1e-9  # max absolute gap between API numbers and Parquet
NAMES = ["BAK1", "CEBPE", "CEBPE_KLF1", "JUN_CEBPA", "KLF1", "KLF1_BAK1"]  # tiny fixture, sorted
DECOY_DATASET = "DecoyDataset"
DECOY_ONLY = "DECOY_ONLY"  # perturbation that exists only in the decoy dataset
DECOY_GENE = "DECOYGENE"  # top gene that exists only in the decoy dataset
DEAD_URI = "mongodb://127.0.0.1:1"  # nothing listens here


@pytest.fixture(scope="session")
def mongo() -> Iterator[MongoClient]:
    """Connect to the MongoDB server the tests use; fail setup if it doesn't answer.

    Yields:
        Client for MONGODB_URI, closed after the session.

    Raises:
        pytest.fail.Exception: MONGODB_URI is unset or the server doesn't answer a ping.
    """
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        pytest.fail("MONGODB_URI not set: run tests with `uv run --env-file .env pytest`.")
    client = MongoClient(uri, serverSelectionTimeoutMS=2_000)
    try:
        client.admin.command("ping")
    except PyMongoError as e:
        client.close()
        pytest.fail(f"MongoDB unreachable at {uri}: start it with `docker compose up -d` ({e})")
    yield client
    client.close()


def decoy_documents(spark_dir: Path) -> list[dict]:
    """Build another dataset's records that a dataset-scoped query must never return.

    Same perturbation names as the fixture with every number shifted, plus one
    perturbation and one gene that exist only in the decoy dataset.

    Args:
        spark_dir: Tiny fixture's Spark output folder.

    Returns:
        Documents labeled DECOY_DATASET.
    """
    docs = load_mongo.build_documents(load_mongo.load_tables(spark_dir), DECOY_DATASET)
    for doc in docs:
        doc["cell_count"] += 1_000_000
        for gene in doc["top_genes"]:
            gene["change"] += 100
        for neighbors in doc["similar"].values():
            for neighbor in neighbors:
                neighbor["distance"] += 100
    only = {**docs[0], "name": DECOY_ONLY, "target_genes": [DECOY_ONLY]}
    only["top_genes"] = [{"gene": DECOY_GENE, "change": 1.0}, *docs[0]["top_genes"][1:]]
    return [*docs, only]


@pytest.fixture(scope="session")
def api_db(mongo: MongoClient, tiny: Path) -> Iterator[Database]:
    """Fill a uniquely named disposable database from the tiny fixture's Spark output.

    The fixture loads under the API's dataset label; decoy records load under
    another label. Only this generated database is dropped, also when loading
    or a test fails.

    Args:
        mongo: Client for the test MongoDB server.
        tiny: Folder holding the fixture's spark/ output.

    Yields:
        The disposable database.
    """
    name = f"minixell_test_{uuid.uuid4().hex[:12]}"
    assert name != load_mongo.DB_NAME
    db = mongo[name]
    try:
        collection = db[load_mongo.COLLECTION]
        load_mongo.run(tiny / "spark", collection, DATASET)
        load_mongo.write_documents(collection, decoy_documents(tiny / "spark"), DECOY_DATASET)
        yield db
    finally:
        mongo.drop_database(name)


@pytest.fixture
def client(api_db: Database, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Run the app, startup and shutdown included, against the disposable database.

    Args:
        api_db: Disposable database the app reads.
        monkeypatch: Sets MONGODB_DB for this test only.

    Yields:
        Client sending in-process HTTP requests to the app.
    """
    monkeypatch.setenv("MONGODB_DB", api_db.name)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def parquet(tiny: Path) -> dict[str, pd.DataFrame]:
    """Read the Spark tables the API's answers must match.

    Args:
        tiny: Folder holding the fixture's spark/ output.

    Returns:
        Table name to DataFrame for perturbations, top_genes, similar_euclidean,
        and similar_edistance.
    """
    return {t: pd.read_parquet(tiny / "spark" / t) for t in load_mongo.TABLES}


def ranked(table: pd.DataFrame, name: str, cols: list[str]) -> list[tuple]:
    """List one perturbation's ranked rows from a Spark table.

    Args:
        table: top_genes or a similar_* table.
        name: Perturbation whose rows to return.
        cols: Columns to keep, in tuple order.

    Returns:
        Row tuples in rank order.
    """
    rows = table[table["perturbation"] == name].sort_values("rank")
    return list(rows[cols].itertuples(index=False, name=None))


def assert_pairs(actual: list[dict], keys: tuple[str, str], expected: list[tuple]) -> None:
    """Check (label, number) lists match in order: labels exactly, numbers within TOL.

    Args:
        actual: Response entries, e.g. {"gene": ..., "change": ...}.
        keys: Label key and number key in each entry.
        expected: (label, number) tuples from Parquet in expected order.
    """
    label, number = keys
    assert [e[label] for e in actual] == [x[0] for x in expected]
    assert [e[number] for e in actual] == pytest.approx([x[1] for x in expected], abs=TOL)


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_unreachable(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", DEAD_URI)
    with TestClient(app) as dead:
        r = dead.get("/health")
    assert r.status_code == 503


@pytest.mark.parametrize("name", NAMES)
def test_get_perturbation(client, parquet, name):
    r = client.get(f"/perturbations/{name}")
    assert r.status_code == 200
    doc = r.json()
    assert "_id" not in doc
    row = parquet["perturbations"].set_index("name").loc[name]
    assert doc["dataset"] == DATASET
    assert doc["name"] == name
    assert doc["target_genes"] == list(row["target_genes"]) == name.split("_")
    assert doc["cell_count"] == row["cell_count"]
    assert doc["sampled_cell_count"] == row["sampled_cell_count"]
    assert_pairs(doc["top_genes"], ("gene", "change"), ranked(parquet["top_genes"], name, ["gene", "change"]))
    for metric in ("euclidean", "edistance"):
        expected = ranked(parquet[f"similar_{metric}"], name, ["neighbor", "distance"])
        assert len(expected) == len(NAMES) - 1
        assert_pairs(doc["similar"][metric], ("name", "distance"), expected)


@pytest.mark.parametrize("name", ["NOPE", DECOY_ONLY])
def test_get_unknown_is_404(client, name):
    assert client.get(f"/perturbations/{name}").status_code == 404


def test_list_all(client, parquet):
    r = client.get("/perturbations")
    assert r.status_code == 200
    rows = r.json()
    assert sorted(parquet["perturbations"]["name"]) == NAMES
    assert [x["name"] for x in rows] == NAMES
    meta = parquet["perturbations"].set_index("name")
    for x in rows:
        assert x["target_genes"] == list(meta.loc[x["name"], "target_genes"])
        assert x["cell_count"] == meta.loc[x["name"], "cell_count"]
        assert x["gene_change"] is None


@pytest.mark.parametrize("limit", [1, 3])
def test_list_limit_returns_prefix(client, limit):
    r = client.get("/perturbations", params={"limit": limit})
    assert [x["name"] for x in r.json()] == NAMES[:limit]


def test_search_by_gene(client, parquet):
    top = parquet["top_genes"]
    for gene, rows in top.groupby("gene"):
        expected = sorted(zip(rows["perturbation"], rows["change"]))
        r = client.get("/perturbations", params={"gene": gene})
        assert r.status_code == 200
        assert_pairs(r.json(), ("name", "gene_change"), expected)


def test_search_unknown_or_wrong_case_is_empty(client, parquet):
    genes = set(parquet["top_genes"]["gene"])
    wrong_case = next(g.lower() for g in sorted(genes) if g.lower() not in genes)
    for gene in ["NOTAGENE", wrong_case, DECOY_GENE]:
        r = client.get("/perturbations", params={"gene": gene})
        assert r.status_code == 200
        assert r.json() == []


@pytest.mark.parametrize("limit", [1, MAX_LIMIT])
def test_limit_bounds_accepted(client, limit):
    r = client.get("/perturbations", params={"limit": limit})
    assert r.status_code == 200
    assert len(r.json()) == min(limit, len(NAMES))


@pytest.mark.parametrize("limit", ["0", "-1", str(MAX_LIMIT + 1), "abc", "1.5"])
def test_limit_invalid_is_422(client, limit):
    assert client.get("/perturbations", params={"limit": limit}).status_code == 422


@pytest.mark.parametrize("metric", ["euclidean", "edistance"])
@pytest.mark.parametrize("name", NAMES)
def test_similar(client, parquet, name, metric):
    r = client.get(f"/perturbations/{name}/similar", params={"metric": metric})
    assert r.status_code == 200
    body = r.json()
    assert (body["name"], body["metric"]) == (name, metric)
    assert name not in [n["name"] for n in body["neighbors"]]
    distances = [n["distance"] for n in body["neighbors"]]
    assert distances == sorted(distances)
    expected = ranked(parquet[f"similar_{metric}"], name, ["neighbor", "distance"])
    assert_pairs(body["neighbors"], ("name", "distance"), expected)


def test_similar_defaults_to_edistance(client, parquet):
    body = client.get("/perturbations/KLF1/similar").json()
    assert body["metric"] == "edistance"
    expected = ranked(parquet["similar_edistance"], "KLF1", ["neighbor", "distance"])
    assert_pairs(body["neighbors"], ("name", "distance"), expected)


@pytest.mark.parametrize("name", ["NOPE", DECOY_ONLY])
def test_similar_unknown_is_404(client, name):
    assert client.get(f"/perturbations/{name}/similar").status_code == 404


def test_similar_invalid_metric_is_422(client):
    assert client.get("/perturbations/KLF1/similar", params={"metric": "cosine"}).status_code == 422
