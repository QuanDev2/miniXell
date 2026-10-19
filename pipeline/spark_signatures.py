"""Compute signatures and distances with PySpark in local mode from Parquet.

data/processed/<name>/cells.parquet -> cells per perturbation
  -> data/processed/<name>/spark/perturbations/
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
    cells = spark.read.parquet(str(src / "cells.parquet"))

    tables = {"perturbations": perturbation_table(cells)}
    for table_name, table in tables.items():
        table.write.mode("overwrite").parquet(str(out / table_name))
        log(start, f"wrote spark/{table_name}/ ({spark.read.parquet(str(out / table_name)).count():,} rows)")

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
