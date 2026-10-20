"""Compute signatures and distances with PySpark in local mode from Parquet.

data/processed/<name>/{cells,expression}.parquet -> cells per perturbation
  -> gene sums per perturbation -> full grid of averages -> minus control averages -> top genes per perturbation
  -> Euclidean pair distances -> nearest perturbations
  -> data/processed/<name>/spark/{perturbations,signatures,top_genes,euclidean,similar_euclidean}/
"""

import argparse
import time

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from pipeline.convert import COLUMNS, PROCESSED_DIR, log

DRIVER_MEMORY = "8g"
N_TOP = 50  # genes kept per perturbation
N_SIMILAR = 20  # neighbors kept per perturbation


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


def top_genes(sig: DataFrame) -> DataFrame:
    """Keep each perturbation's N_TOP genes by absolute change; ties by gene name A-Z.

    In: signatures.
    Out: plan for table (perturbation, rank, gene, change); rank 1 = largest move.
    """
    by_size = Window.partitionBy("perturbation").orderBy(F.abs("change").desc(), F.col("gene").asc())
    return (
        sig.withColumn("rank", F.row_number().over(by_size))
        .where(F.col("rank") <= N_TOP)
        .select("perturbation", "rank", "gene", "change")
    )


def euclidean(sig: DataFrame) -> DataFrame:
    """Compute straight-line distance between every pair of signatures.

    In: signatures.
    Out: plan for table (a, b, distance), one row per pair, a before b alphabetically.
    """
    a = sig.select(F.col("perturbation").alias("a"), "gene", F.col("change").alias("change_a"))
    b = sig.select(F.col("perturbation").alias("b"), "gene", F.col("change").alias("change_b"))
    return (
        a.join(b, on="gene")
        .where(F.col("a") < F.col("b"))
        .groupBy("a", "b")
        .agg(F.sqrt(F.sum((F.col("change_a") - F.col("change_b")) ** 2)).alias("distance"))
    )


def nearest(pairs: DataFrame) -> DataFrame:
    """Pick each perturbation's N_SIMILAR closest others; ties by neighbor name A-Z.

    In: pair distances (a, b, distance).
    Out: plan for table (perturbation, rank, neighbor, distance).
    """
    both = pairs.select(F.col("a").alias("perturbation"), F.col("b").alias("neighbor"), "distance").unionByName(
        pairs.select(F.col("b").alias("perturbation"), F.col("a").alias("neighbor"), "distance")
    )
    closest = Window.partitionBy("perturbation").orderBy("distance", "neighbor")
    return (
        both.withColumn("rank", F.row_number().over(closest))
        .where(F.col("rank") <= N_SIMILAR)
        .select("perturbation", "rank", "neighbor", "distance")
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

    sig = signatures(cells, expression, control)
    pairs = euclidean(sig).cache()  # used 3 times: written, both sides of nearest's union
    tables = {
        "perturbations": perturbation_table(cells),
        "signatures": sig,
        "top_genes": top_genes(sig),
        "euclidean": pairs,
        "similar_euclidean": nearest(pairs),
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
