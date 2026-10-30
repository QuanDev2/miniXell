"""Fetch public gene descriptions for every top gene and store them in MongoDB.

Collect the distinct genes in data/processed/<name>/spark/top_genes/, look each
up at mygene.info (NCBI Gene summaries), and upsert one document per gene into
minixell.genes. Genes not found by symbol are retried under former names, since
the dataset uses names that have since changed. These descriptions are the only
outside facts the explain endpoint gives Claude.

MONGODB_URI selects the server. Re-runs update documents in place.
"""

import argparse
import json
import os
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from pymongo import MongoClient, ReplaceOne
from pymongo.collection import Collection

from pipeline.convert import PROCESSED_DIR, log
from pipeline.load_mongo import DATASET_LABELS, DB_NAME

COLLECTION = "genes"
MYGENE_URL = "https://mygene.info/v3/query"
SOURCE = "mygene.info"
BATCH = 1_000  # mygene.info's maximum terms per POST query
FALLBACK_SCOPES = "alias,ensembl.gene,accession"  # former names and IDs


def top_gene_symbols(spark_dir: Path) -> list[str]:
    """List the distinct genes that appear in any perturbation's top genes.

    Args:
        spark_dir: Dataset's Spark output folder containing top_genes/.

    Returns:
        Gene symbols as the dataset spells them, sorted A to Z.
    """
    return sorted(pd.read_parquet(spark_dir / "top_genes", columns=["gene"])["gene"].unique())


def query_mygene(terms: list[str], scopes: str) -> dict[str, dict]:
    """Look up human genes at mygene.info and keep one match per term.

    Args:
        terms: Gene symbols or former names to search for.
        scopes: mygene.info fields the terms are matched against, such as
            "symbol" or FALLBACK_SCOPES.

    Returns:
        Each found term mapped to its best match, with symbol, name, and
        summary when present. A match whose symbol equals the term wins;
        otherwise mygene.info's top-scored match. Unfound terms are absent.

    Raises:
        urllib.error.URLError: mygene.info is unreachable or returns an error.
    """
    best: dict[str, dict] = {}
    for i in range(0, len(terms), BATCH):
        body = json.dumps({
            "q": terms[i:i + BATCH], "scopes": scopes, "species": "human",
            "fields": "symbol,name,summary",
        }).encode()
        request = urllib.request.Request(MYGENE_URL, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            hits = json.load(response)
        for hit in hits:  # hits for one term arrive in mygene.info's score order
            term = hit["query"]
            if hit.get("notfound"):
                continue
            if term not in best or (hit.get("symbol") == term != best[term].get("symbol")):
                best[term] = hit
    return best


def build_documents(symbols: list[str], hits: dict[str, dict], fetched_at: datetime) -> list[dict]:
    """Assemble one genes document per dataset symbol.

    Args:
        symbols: Gene symbols as the dataset spells them.
        hits: Best mygene.info match per symbol; symbols without one are
            stored with null fields.
        fetched_at: Time of the lookup, stored on every document.

    Returns:
        Documents keyed by the dataset's symbol, with current_symbol holding
        today's official name (null when not found) and summary null when
        mygene.info has no description.
    """
    docs = []
    for symbol in symbols:
        hit = hits.get(symbol, {})
        docs.append({
            "symbol": symbol,
            "current_symbol": hit.get("symbol"),
            "full_name": hit.get("name"),
            "summary": hit.get("summary"),
            "source": SOURCE,
            "fetched_at": fetched_at,
        })
    return docs


def write_documents(collection: Collection, docs: list[dict]) -> int:
    """Insert or replace each gene's document by symbol.

    Args:
        collection: MongoDB collection holding one description per symbol.
        docs: Documents from build_documents.

    Returns:
        Number of documents inserted rather than replaced.
    """
    result = collection.bulk_write([ReplaceOne({"symbol": d["symbol"]}, d, upsert=True) for d in docs])
    return result.upserted_count


def run(spark_dir: Path, collection: Collection) -> None:
    """Fetch descriptions for one dataset's top genes and store them.

    Args:
        spark_dir: Dataset's Spark output folder consumed by top_gene_symbols.
        collection: Destination genes collection; main selects minixell.genes.
    """
    start = time.perf_counter()
    symbols = top_gene_symbols(spark_dir)
    hits = query_mygene(symbols, "symbol")
    missing = [s for s in symbols if s not in hits]
    renamed = query_mygene(missing, FALLBACK_SCOPES) if missing else {}
    hits |= renamed
    docs = build_documents(symbols, hits, datetime.now(UTC))
    described = sum(d["summary"] is not None for d in docs)
    log(start, f"{len(symbols)} genes: {len(symbols) - len(missing)} by symbol, {len(renamed)} by former name, "
               f"{len(symbols) - len(hits)} not found; {described} with a description")
    collection.create_index("symbol", unique=True)
    inserted = write_documents(collection, docs)
    log(start, f"wrote {len(docs)} documents to {collection.full_name} ({inserted} new)")


def main() -> None:
    """Fetch descriptions for command-line datasets into minixell.genes.

    Raises:
        KeyError: MONGODB_URI is absent from the environment.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="+", choices=sorted(DATASET_LABELS))
    args = parser.parse_args()
    with MongoClient(os.environ["MONGODB_URI"]) as client:
        for name in args.names:
            run(PROCESSED_DIR / name / "spark", client[DB_NAME][COLLECTION])


if __name__ == "__main__":
    main()
