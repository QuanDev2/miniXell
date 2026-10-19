"""Compute signatures and distances with PySpark in local mode from Parquet.

data/processed/<name>/{cells,expression}.parquet -> cells per perturbation
  -> gene sums per perturbation -> full grid of averages -> minus control averages
  -> data/processed/<name>/spark/{perturbations,signatures}/
"""

import argparse
import time

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from pipeline.convert import COLUMNS, PROCESSED_DIR, log

DRIVER_MEMORY = "8g"


def session() -> SparkSession:
    """Start local Spark: one driver, one worker per CPU core.

    In: none.
    Out: Spark session.
    """
    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("minixell-signatures")
        .config("spark.driver.memory", DRIVER_MEMORY)
        .config("spark.ui.showConsoleProgress", "false")  # progress bar overwrites log lines
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def perturbation_table(cells: DataFrame) -> DataFrame:
    """List perturbations with target genes and cell counts; control excluded.

    In: cells (cell_id, perturbation, is_control, ...).
    Out: plan for table (name, target_genes, cell_count).
    """
    return (
        cells.where(~F.col("is_control"))
        .groupBy(F.col("perturbation").alias("name"))
        .agg(F.count("*").alias("cell_count"))
        .withColumn("target_genes", F.split("name", "_"))
        .select("name", "target_genes", "cell_count")
    )


def gene_sums(cells: DataFrame, expression: DataFrame) -> DataFrame:
    """Sum each gene's values per perturbation, control included.

    In: cells, expression (non-zero only).
    Out: plan for table (perturbation, gene, total); only pairs with rows.
    """
    return (
        expression
        .join(F.broadcast(cells.select("cell_id", "perturbation")), on="cell_id")  # small table to every worker
        .groupBy("perturbation", "gene")
        .agg(F.sum(F.col("value").cast("double")).alias("total"))
    )


def signatures(cells: DataFrame, expression: DataFrame, control: str) -> DataFrame:
    """Subtract control average from each perturbation's average; cells without a row count as zero.

    In: cells, expression, control label.
    Out: plan for table (perturbation, gene, change); control excluded; unordered.
    State: caches averages grid in Spark memory on first action.
    """
    counts = cells.groupBy("perturbation").agg(F.count("*").alias("n_cells"))
    genes = expression.select("gene").distinct()
    means = (
        counts.crossJoin(genes)  # every (perturbation, gene), so zero-only genes keep a row
        .join(gene_sums(cells, expression), on=["perturbation", "gene"], how="left")
        .fillna(0.0, subset=["total"])
        .withColumn("mean", F.col("total") / F.col("n_cells"))
        .cache()  # used twice below; without it the 20M-row sum runs twice
    )
    control_means = means.where(F.col("perturbation") == control).select("gene", F.col("mean").alias("control_mean"))
    return (
        means.where(F.col("perturbation") != control)
        .join(F.broadcast(control_means), on="gene")
        .select("perturbation", "gene", (F.col("mean") - F.col("control_mean")).alias("change"))
    )


def run(name: str, hold: bool) -> None:
    """Build Spark results for one dataset.

    In: dataset name with entry in COLUMNS, whether to keep Spark UI open at end.
    Out: none.
    State: writes data/processed/<name>/spark/.
    """
    start = time.perf_counter()
    spark = session()
    log(start, f"Spark started; UI at {spark.sparkContext.uiWebUrl}")

    src, out = PROCESSED_DIR / name, PROCESSED_DIR / name / "spark"
    control = COLUMNS[name]["control"]
    cells = spark.read.parquet(str(src / "cells.parquet"))
    expression = spark.read.parquet(str(src / "expression.parquet"))

    tables = {
        "perturbations": perturbation_table(cells),
        "signatures": signatures(cells, expression, control),
    }
    for table_name, table in tables.items():
        spark.sparkContext.setJobDescription(f"write {table_name}")
        table.write.mode("overwrite").parquet(str(out / table_name))
        log(start, f"wrote spark/{table_name}/")

    if hold:
        input("Spark UI open; press Enter to stop... ")
    spark.stop()


def main() -> None:
    """Build Spark results for datasets named on the command line.

    In: one or more dataset names; --hold keeps Spark UI open until Enter.
    Out: none.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="+", choices=sorted(COLUMNS))
    parser.add_argument("--hold", action="store_true", help="keep Spark UI open until Enter")
    args = parser.parse_args()
    for name in args.names:
        run(name, args.hold)


if __name__ == "__main__":
    main()
