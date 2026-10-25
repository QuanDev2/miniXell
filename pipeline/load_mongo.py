"""Load Spark results into MongoDB: one document per perturbation.

Read precomputed Spark summaries from data/processed/<name>/spark/ and embed
top genes and both ranked neighbor lists in each perturbation document.
Full signatures and pairwise distance tables remain in Parquet.

The command line accepts dataset names from DATASET_LABELS. MONGODB_URI
selects the server; DB_NAME and COLLECTION select minixell.perturbations.
Each load replaces only the selected dataset's records.
"""

import argparse
import os
import time
from pathlib import Path

import pandas as pd
from pymongo import MongoClient
from pymongo.collection import Collection

from pipeline.convert import PROCESSED_DIR, log

DB_NAME = "minixell"
COLLECTION = "perturbations"
DATASET_LABELS = {"norman": "NormanWeissman2019"}  # CLI name -> document `dataset` field
TABLES = ["perturbations", "top_genes", "similar_euclidean", "similar_edistance"]


def load_tables(spark_dir: Path) -> dict[str, pd.DataFrame]:
    """Read precomputed perturbation summaries and restore ranking order.

    Args:
        spark_dir: Dataset's Spark output folder containing the perturbations,
            top_genes, similar_euclidean, and similar_edistance Parquet folders.

    Returns:
        Tables keyed by folder name. Gene and neighbor rows are sorted by
        perturbation and saved rank; perturbation metadata keeps its read order.
    """
    tables = {name: pd.read_parquet(spark_dir / name) for name in TABLES}
    for name in TABLES[1:]:
        tables[name] = tables[name].sort_values(["perturbation", "rank"], ignore_index=True)
    return tables


def ranked_lists(table: pd.DataFrame, fields: dict[str, str]) -> dict[str, list[dict]]:
    """Nest ranked gene or neighbor rows under each perturbation.

    Args:
        table: Gene or neighbor rows already sorted by perturbation and rank.
        fields: Source columns to retain, mapped to their document field names;
            for example, {"neighbor": "name", "distance": "distance"}.

    Returns:
        Perturbation names mapped to lists of records in input order.
        Only mapped fields are retained; list position carries the rank.
    """
    kept = table[["perturbation", *fields]].rename(columns=fields)
    return {
        name: group.drop(columns="perturbation").to_dict("records")
        for name, group in kept.groupby("perturbation", sort=False)
    }


def build_documents(tables: dict[str, pd.DataFrame], dataset: str) -> list[dict]:
    """Assemble database-ready summaries without recalculating results.

    Args:
        tables: Four tables returned by load_tables, including metadata and
            ranked gene and neighbor rows for every perturbation.
        dataset: Published dataset label stored on every document, such as
            NormanWeissman2019; not the command-line alias norman.

    Returns:
        Documents sorted by perturbation name, with target genes, cell counts,
        top genes, and both neighbor lists embedded in saved rank order.

    Raises:
        KeyError: A required table, column, or perturbation's ranked list
            is missing.
    """
    top = ranked_lists(tables["top_genes"], {"gene": "gene", "change": "change"})
    euclidean = ranked_lists(tables["similar_euclidean"], {"neighbor": "name", "distance": "distance"})
    edistance = ranked_lists(tables["similar_edistance"], {"neighbor": "name", "distance": "distance"})
    return [
        {
            "dataset": dataset,
            "name": row.name,
            "target_genes": list(row.target_genes),
            "cell_count": int(row.cell_count),
            "sampled_cell_count": int(row.sampled_cell_count),
            "top_genes": top[row.name],
            "similar": {"euclidean": euclidean[row.name], "edistance": edistance[row.name]},
        }
        for row in tables["perturbations"].sort_values("name").itertuples(index=False)
    ]


def ensure_indexes(collection: Collection) -> None:
    """Index perturbation identities and changed-gene lookups.

    Args:
        collection: Destination MongoDB collection holding perturbation
            summaries, one record per dataset and perturbation name.

    Existing matching indexes are reused. The unique (dataset, name) index
    prevents duplicate summaries within a dataset; the top_genes.gene index
    supports finding summaries containing a gene in their top-gene lists.
    """
    collection.create_index([("dataset", 1), ("name", 1)], unique=True)
    collection.create_index("top_genes.gene")


def write_documents(collection: Collection, docs: list[dict], dataset: str) -> int:
    """Replace stored perturbation summaries for one dataset.

    Args:
        collection: Caller-selected MongoDB collection holding perturbation
            summaries, one record per dataset and perturbation name.
        docs: Complete, nonempty replacement records for the selected dataset.
            Insertion adds missing _id fields to these dictionaries in place.
        dataset: Exact stored dataset label identifying records to delete.

    Returns:
        Number of existing records deleted.

    Warning:
        Deletes before inserting, without a transaction. Insertion failure
        can leave the dataset empty or partially loaded. Other datasets'
        existing records are not deleted.
    """
    deleted = collection.delete_many({"dataset": dataset}).deleted_count
    collection.insert_many(docs)
    return deleted


def run(spark_dir: Path, collection: Collection, dataset: str) -> None:
    """Publish one dataset's Spark summaries to MongoDB.

    Args:
        spark_dir: Dataset's Spark output folder consumed by load_tables.
        collection: Destination MongoDB collection for perturbation summaries;
            main selects minixell.perturbations.
        dataset: Published dataset label attached to new records and used
            to select existing records for replacement.

    Document assembly and index creation finish before existing records are
    deleted. Replacement has the non-atomic failure risk in write_documents.
    """
    start = time.perf_counter()
    docs = build_documents(load_tables(spark_dir), dataset)
    log(start, f"built {len(docs)} documents from {spark_dir}")
    ensure_indexes(collection)
    deleted = write_documents(collection, docs, dataset)
    log(start, f"replaced {deleted} documents with {len(docs)} in {collection.full_name} ({dataset})")


def main() -> None:
    """Load command-line datasets into minixell.perturbations.

    Accept one or more aliases from DATASET_LABELS, such as norman. Read each
    alias's Spark output and store records under its published dataset label.
    Connect through MONGODB_URI and close the client when loading finishes.

    Raises:
        KeyError: MONGODB_URI is absent from the environment.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="+", choices=sorted(DATASET_LABELS))
    args = parser.parse_args()
    with MongoClient(os.environ["MONGODB_URI"]) as client:
        collection = client[DB_NAME][COLLECTION]
        for name in args.names:
            run(PROCESSED_DIR / name / "spark", collection, DATASET_LABELS[name])


if __name__ == "__main__":
    main()
