"""Compute single-machine reference results (the answer key) from Parquet.

data/processed/<name>/{cells,expression}.parquet -> per-gene averages -> signatures -> ranked genes
  -> pair distances -> nearest perturbations
  -> data/processed/<name>/legacy/{perturbations,signatures,top_genes,euclidean,similar_euclidean}.parquet
"""

import argparse
import resource
import time

import numpy as np
import pandas as pd

from pipeline.convert import COLUMNS, PROCESSED_DIR, log

N_TOP = 50  # genes kept per perturbation
N_SIMILAR = 20  # neighbors kept per perturbation per metric


def load(name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read cells and expression tables.

    In: dataset name.
    Out: cells (cell_id, perturbation), expression (cell_id, gene, value; non-zero only).
    """
    src = PROCESSED_DIR / name
    cells = pd.read_parquet(src / "cells.parquet", columns=["cell_id", "perturbation"])
    expression = pd.read_parquet(src / "expression.parquet")
    return cells, expression


def gene_means(cells: pd.DataFrame, expression: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Average each gene per perturbation; cells without a row count as zero.

    In: cells, expression.
    Out: grid of averages (rows: perturbations + control, columns: genes), cell count per row.
    """
    counts = cells["perturbation"].value_counts().sort_index()
    groups = expression["cell_id"].map(cells.set_index("cell_id")["perturbation"]).rename("perturbation")
    sums = (
        expression["value"].astype(np.float64)
        .groupby([groups, expression["gene"]], observed=True)
        .sum()
        .unstack(fill_value=0.0)
    )
    genes = expression["gene"].cat.categories.astype(str)
    sums = sums.reindex(index=counts.index, columns=genes, fill_value=0.0)  # gene with no rows in a group = 0
    return sums.div(counts, axis=0), counts


def signatures(means: pd.DataFrame, control: str) -> pd.DataFrame:
    """Subtract control average from each perturbation's average.

    In: grid of averages, control label.
    Out: long table (perturbation, gene, change), sorted by perturbation then gene.
    """
    grid = means.drop(index=control) - means.loc[control]
    grid.index.name, grid.columns.name = "perturbation", "gene"
    sig = grid.stack().rename("change").reset_index()
    sig["perturbation"] = sig["perturbation"].astype(str)
    sig["gene"] = sig["gene"].astype(str)
    return sig.sort_values(["perturbation", "gene"], ignore_index=True)


def rank_genes(sig: pd.DataFrame) -> pd.DataFrame:
    """Rank genes within each perturbation by absolute change; ties by gene name A-Z.

    In: signatures.
    Out: signatures plus rank (1 = largest move), ordered by perturbation then rank.
    """
    ranked = sig.assign(size=sig["change"].abs()).sort_values(
        ["perturbation", "size", "gene"], ascending=[True, False, True], ignore_index=True
    )
    ranked["rank"] = ranked.groupby("perturbation", sort=False).cumcount() + 1
    return ranked.drop(columns="size")


def perturbation_table(counts: pd.Series, control: str) -> pd.DataFrame:
    """List perturbations with target genes and cell counts; control excluded.

    In: cell count per label, control label.
    Out: table (name, target_genes, cell_count).
    """
    table = counts.drop(control).rename("cell_count").rename_axis("name").reset_index()
    table["name"] = table["name"].astype(str)
    table["target_genes"] = table["name"].str.split("_")
    return table[["name", "target_genes", "cell_count"]]


def check_targets(ranked: pd.DataFrame) -> None:
    """Print where each single-gene perturbation's target ranks in its own signature.

    In: ranked signatures.
    Out: none; prints report.
    """
    single = ~ranked["perturbation"].str.contains("_")
    n_single = ranked.loc[single, "perturbation"].nunique()
    hits = ranked[single & (ranked["gene"] == ranked["perturbation"])]
    print(f"  target check: {len(hits)} of {n_single} single-gene targets in gene list")
    print(
        f"    rank #1: {(hits['rank'] == 1).sum()}   top 10: {(hits['rank'] <= 10).sum()}   "
        f"top 50: {(hits['rank'] <= N_TOP).sum()}   moved up: {(hits['change'] > 0).sum()}"
    )
    worst = hits.nlargest(5, "rank")
    print("    worst: " + ", ".join(f"{r.gene} (rank {r.rank}, {r.change:+.2f})" for r in worst.itertuples()))


def euclidean(sig: pd.DataFrame) -> pd.DataFrame:
    """Compute straight-line distance between every pair of signatures.

    In: signatures.
    Out: table (a, b, distance), one row per pair, a before b alphabetically.
    """
    grid = sig.pivot(index="perturbation", columns="gene", values="change")  # rows sorted by name
    names, values = grid.index.to_numpy(), grid.to_numpy()
    parts = [
        pd.DataFrame({"a": names[i], "b": names[i + 1:], "distance": np.sqrt(((values[i + 1:] - values[i]) ** 2).sum(axis=1))})
        for i in range(len(names) - 1)
    ]
    return pd.concat(parts, ignore_index=True)


def nearest(pairs: pd.DataFrame) -> pd.DataFrame:
    """Pick each perturbation's closest others; ties by neighbor name A-Z.

    In: pair distances (a, b, distance).
    Out: table (perturbation, rank, neighbor, distance), N_SIMILAR rows per perturbation.
    """
    both = pd.concat([
        pairs.rename(columns={"a": "perturbation", "b": "neighbor"}),
        pairs.rename(columns={"b": "perturbation", "a": "neighbor"}),
    ], ignore_index=True).sort_values(["perturbation", "distance", "neighbor"], ignore_index=True)
    both["rank"] = both.groupby("perturbation", sort=False).cumcount() + 1
    return both.loc[both["rank"] <= N_SIMILAR, ["perturbation", "rank", "neighbor", "distance"]]


def check_similar(similar: pd.DataFrame, example: str) -> None:
    """Print list-size and self-match checks plus one example's closest neighbors.

    In: nearest table, example perturbation name.
    Out: none; prints report.
    """
    sizes = similar.groupby("perturbation").size()
    selfs = (similar["perturbation"] == similar["neighbor"]).sum()
    print(f"  similar check: {len(sizes)} lists, sizes {sizes.min()}-{sizes.max()}, self matches {selfs}")
    top = similar[similar["perturbation"] == example].head(5)
    print(f"    {example}: " + ", ".join(f"{r.neighbor} ({r.distance:.3f})" for r in top.itertuples()))


def run(name: str) -> None:
    """Build answer key for one dataset.

    In: dataset name with entry in COLUMNS.
    Out: none.
    State: writes data/processed/<name>/legacy/.
    """
    start = time.perf_counter()
    control = COLUMNS[name]["control"]
    cells, expression = load(name)
    log(start, f"loaded {len(cells):,} cells, {len(expression):,} expression rows")

    means, counts = gene_means(cells, expression)
    log(start, f"averaged {means.shape[1]:,} genes over {means.shape[0]} groups ({control} included)")

    sig = signatures(means, control)
    ranked = rank_genes(sig)
    log(start, f"signatures: {sig['perturbation'].nunique()} perturbations x {sig['gene'].nunique():,} genes")

    pairs = euclidean(sig)
    similar = nearest(pairs)
    log(start, f"euclidean: {len(pairs):,} pairs")

    out = PROCESSED_DIR / name / "legacy"
    out.mkdir(parents=True, exist_ok=True)
    tables = {
        "perturbations": perturbation_table(counts, control),
        "signatures": sig,
        "top_genes": ranked.loc[ranked["rank"] <= N_TOP, ["perturbation", "rank", "gene", "change"]],
        "euclidean": pairs,
        "similar_euclidean": similar,
    }
    for table_name, table in tables.items():
        table.to_parquet(out / f"{table_name}.parquet", index=False)
        log(start, f"wrote legacy/{table_name}.parquet ({len(table):,} rows)")

    check_targets(ranked)
    check_similar(similar, "KLF1")
    for f in sorted(out.glob("*.parquet")):
        print(f"  {f.name}: {f.stat().st_size / 1e6:.1f} MB")
    peak_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9  # macOS reports bytes
    print(f"  peak memory: {peak_gb:.1f} GB")


def main() -> None:
    """Build answer keys for datasets named on the command line.

    In: one or more dataset names.
    Out: none.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="+", choices=sorted(COLUMNS))
    for name in parser.parse_args().names:
        run(name)


if __name__ == "__main__":
    main()
