"""Convert a downloaded h5ad dataset into Spark-ready Parquet files.

data/raw/<file>.h5ad -> filter -> normalize + log -> top genes -> PCA
  -> data/processed/<name>/{cells,expression,cell_pcs}.parquet
"""

import argparse
import resource
import time
from pathlib import Path

import anndata as ad
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import scanpy as sc

from pipeline.download import DATASETS, RAW_DIR

PROCESSED_DIR = Path("data/processed")
TARGET_SUM = 10_000  # counts per cell after normalization
N_TOP_GENES = 2_000
N_PCS = 50
MITO_MAX = 20.0  # percent; cells at or above are dropped
SEED = 0
ROWS_PER_CHUNK = 10_000  # cells per expression write batch

COLUMNS = {  # name -> obs columns: perturbation label, control label, batch, mito percent
    "norman": {"label": "perturbation", "control": "control", "batch": "gemgroup", "mito": "percent_mito"},
}


def log(start: float, message: str) -> None:
    """Print message with elapsed seconds.

    In: start time, message.
    Out: none.
    """
    print(f"[{time.perf_counter() - start:6.1f}s] {message}")


def preprocess(adata: ad.AnnData, cols: dict, start: float) -> ad.AnnData:
    """Filter cells, normalize, keep top genes, compute PCs.

    In: raw-count AnnData, obs column names, start time.
    Out: AnnData with log-normalized top genes in X and PCs in obsm["X_pca"].
    """
    keep = adata.obs[cols["mito"]] < MITO_MAX
    adata = adata[keep].copy()
    log(start, f"dropped {int((~keep).sum())} cells with {cols['mito']} >= {MITO_MAX}; {adata.n_obs} remain")

    adata.X = adata.X.tocsr()  # row-compressed: fast per-cell access
    sc.pp.normalize_total(adata, target_sum=TARGET_SUM)  # totals over all genes, before gene selection
    sc.pp.log1p(adata)
    log(start, f"normalized to {TARGET_SUM} per cell and log-transformed")

    sc.pp.highly_variable_genes(adata, n_top_genes=N_TOP_GENES)
    adata = adata[:, adata.var["highly_variable"]].copy()
    log(start, f"kept {adata.n_vars} most variable genes")

    sc.pp.pca(adata, n_comps=N_PCS, random_state=SEED)
    log(start, f"computed {N_PCS} principal components")
    return adata


def write_cells(adata: ad.AnnData, cols: dict, out: Path) -> None:
    """Write one row per cell: id, perturbation, control flag, batch.

    In: preprocessed AnnData, obs column names, output dir.
    Out: none; writes cells.parquet.
    """
    labels = adata.obs[cols["label"]].astype(str).to_numpy()
    table = pa.table({
        "cell_id": adata.obs_names.to_numpy(dtype=str),
        "perturbation": labels,
        "is_control": labels == cols["control"],
        "gemgroup": adata.obs[cols["batch"]].to_numpy(dtype=np.int32),
    })
    pq.write_table(table, out / "cells.parquet")


def write_expression(adata: ad.AnnData, out: Path) -> int:
    """Write one row per non-zero (cell, gene) value, in batches of cells.

    In: preprocessed AnnData with CSR X, output dir.
    Out: rows written.
    """
    cell_ids = pa.array(adata.obs_names.to_numpy(dtype=str))
    genes = pa.array(adata.var_names.to_numpy(dtype=str))
    schema = pa.schema([
        ("cell_id", pa.dictionary(pa.int32(), pa.string())),
        ("gene", pa.dictionary(pa.int32(), pa.string())),
        ("value", pa.float32()),
    ])
    rows = 0
    with pq.ParquetWriter(out / "expression.parquet", schema) as writer:
        for first in range(0, adata.n_obs, ROWS_PER_CHUNK):
            block = adata.X[first:first + ROWS_PER_CHUNK].tocoo()
            table = pa.table({
                "cell_id": pa.DictionaryArray.from_arrays((block.row + first).astype(np.int32), cell_ids),
                "gene": pa.DictionaryArray.from_arrays(block.col.astype(np.int32), genes),
                "value": block.data.astype(np.float32),
            }, schema=schema)
            writer.write_table(table)
            rows += table.num_rows
    return rows


def write_pcs(adata: ad.AnnData, out: Path) -> None:
    """Write one row per cell: id plus PC coordinates.

    In: AnnData with obsm["X_pca"], output dir.
    Out: none; writes cell_pcs.parquet.
    """
    pcs = adata.obsm["X_pca"].astype(np.float32)
    columns = {"cell_id": adata.obs_names.to_numpy(dtype=str)}
    columns.update({f"pc_{i + 1}": pcs[:, i] for i in range(pcs.shape[1])})
    pq.write_table(pa.table(columns), out / "cell_pcs.parquet")


def convert(name: str) -> Path:
    """Convert one dataset end to end.

    In: dataset name with entries in DATASETS and COLUMNS.
    Out: output directory.
    State: writes data/processed/<name>/.
    """
    start = time.perf_counter()
    cols = COLUMNS[name]
    adata = ad.read_h5ad(RAW_DIR / DATASETS[name][0])
    log(start, f"loaded {adata.n_obs} cells x {adata.n_vars} genes")

    adata = preprocess(adata, cols, start)

    out = PROCESSED_DIR / name
    out.mkdir(parents=True, exist_ok=True)
    write_cells(adata, cols, out)
    rows = write_expression(adata, out)
    write_pcs(adata, out)
    log(start, f"wrote cells, expression ({rows:,} rows), cell_pcs to {out}")

    for f in sorted(out.glob("*.parquet")):
        print(f"  {f.name}: {f.stat().st_size / 1e6:.1f} MB")
    peak_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9  # macOS reports bytes
    print(f"  peak memory: {peak_gb:.1f} GB")
    return out


def main() -> None:
    """Convert datasets named on the command line.

    In: one or more dataset names.
    Out: none.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="+", choices=sorted(COLUMNS))
    for name in parser.parse_args().names:
        convert(name)


if __name__ == "__main__":
    main()
