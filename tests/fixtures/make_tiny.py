"""Cut a tiny, committed slice of Norman for the parity test.

data/processed/norman/{cells,expression,cell_pcs}.parquet -> 6 perturbations + control, 40 genes
  -> tests/fixtures/tiny/{cells,expression,cell_pcs}.parquet
Source: Norman et al. 2019 via scPerturb (CC BY 4.0).
"""

import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[2]
SRC = ROOT / "data/processed/norman"
OUT = Path(__file__).parent / "tiny"

CONTROL = "control"
PERTURBATIONS = ["KLF1", "BAK1", "CEBPE", "KLF1_BAK1", "CEBPE_KLF1", "JUN_CEBPA"]  # JUN_CEBPA = smallest group
CELLS_PER_GROUP = 30
CONTROL_CELLS = 60
N_GENES = 40


def fingerprint(cell_id: str) -> str:
    """Return MD5 hex of UTF-8 cell_id (same rule as legacy sampling).

    In: cell id.
    Out: 32-char lowercase hex.
    """
    return hashlib.md5(cell_id.encode("utf-8")).hexdigest()


def pick_cells(cells: pd.DataFrame) -> pd.DataFrame:
    """Keep chosen groups; first cells per group by fingerprint.

    In: full cells table.
    Out: CONTROL_CELLS control cells + CELLS_PER_GROUP per perturbation.
    """
    chosen = cells[cells["perturbation"].isin(PERTURBATIONS + [CONTROL])].copy()
    chosen["fp"] = chosen["cell_id"].map(fingerprint)
    chosen = chosen.sort_values(["perturbation", "fp", "cell_id"])
    parts = [
        group.head(CONTROL_CELLS if name == CONTROL else CELLS_PER_GROUP)
        for name, group in chosen.groupby("perturbation")
    ]
    return pd.concat(parts).drop(columns="fp").reset_index(drop=True)


def pick_genes(seen: set[str]) -> list[str]:
    """Return targeted genes plus first others A-Z, N_GENES in total.

    In: genes with at least one row in kept cells.
    Out: gene names.
    """
    targets = sorted({gene for p in PERTURBATIONS for gene in p.split("_")})
    others = sorted(seen - set(targets))[: N_GENES - len(targets)]
    return targets + others


def main() -> None:
    """Build and write the fixture; print size and zero-only coverage.

    In: none.
    Out: none.
    State: writes tests/fixtures/tiny/.
    """
    cells = pick_cells(pd.read_parquet(SRC / "cells.parquet"))
    expression = pd.read_parquet(SRC / "expression.parquet")
    expression = expression[expression["cell_id"].isin(cells["cell_id"])]
    genes = pick_genes(set(expression["gene"].astype(str)))
    expression = expression[expression["gene"].isin(genes)].copy()
    for col in ["cell_id", "gene"]:
        expression[col] = expression[col].cat.remove_unused_categories()  # catalog = kept cells/genes only

    pcs = pd.read_parquet(SRC / "cell_pcs.parquet")
    pcs = pcs[pcs["cell_id"].isin(cells["cell_id"])]

    tagged = expression.merge(cells[["cell_id", "perturbation"]], on="cell_id")
    present = tagged.groupby(["perturbation", "gene"], observed=True).size()
    empty = cells["perturbation"].nunique() * len(genes) - len(present)
    assert empty > 0, "no zero-only genes; pick different genes"
    assert expression["gene"].nunique() == len(genes), "a kept gene has no rows at all"

    OUT.mkdir(parents=True, exist_ok=True)
    cells.to_parquet(OUT / "cells.parquet", index=False)
    expression.to_parquet(OUT / "expression.parquet", index=False)
    pcs.to_parquet(OUT / "cell_pcs.parquet", index=False)
    print(
        f"cells {len(cells)}, expression rows {len(expression)}, genes {len(genes)}, "
        f"zero-only (perturbation, gene) pairs {empty}"
    )


if __name__ == "__main__":
    main()
