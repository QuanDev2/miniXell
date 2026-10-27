"""Shared test setup: run both pipelines on the committed tiny fixture once per session.

tests/fixtures/tiny/ -> legacy + Spark (udf way) -> temp folder with legacy/ and spark/
Parity tests compare the two outputs; API tests load spark/ into a disposable database.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from pipeline import legacy_signatures, spark_signatures

FIXTURE = Path(__file__).parent / "fixtures/tiny"
CONTROL = "control"


def require_java() -> None:
    """Fail setup with a clear message unless a working Java runtime is configured.

    Spark looks for Java at JAVA_HOME first, then on PATH. macOS ships a /usr/bin/java
    stub that exists without a JDK, so the runtime is invoked rather than located.

    Raises:
        pytest.fail.Exception: No Java runtime answers `java -version`.
    """
    java_home = os.environ.get("JAVA_HOME")
    java = str(Path(java_home) / "bin/java") if java_home else shutil.which("java")
    try:
        ok = java is not None and subprocess.run([java, "-version"], capture_output=True).returncode == 0
    except OSError:  # JAVA_HOME points at a folder without bin/java
        ok = False
    if not ok:
        pytest.fail(f"Java 17 not found (tried {java}): Spark needs it. Run tests with `uv run --env-file .env pytest`.")


@pytest.fixture(scope="session")
def tiny(tmp_path_factory) -> Path:
    """Run the legacy and Spark pipelines on the committed tiny fixture.

    Starts and stops Spark once per test session; every test that needs pipeline
    output on the fixture shares this run.

    Args:
        tmp_path_factory: Pytest factory for session-scoped temporary folders.

    Returns:
        Folder holding legacy/ (one Parquet file per table) and spark/ (one
        folder of part files per table).
    """
    require_java()
    out = tmp_path_factory.mktemp("tiny")
    legacy_signatures.run(FIXTURE, out / "legacy", CONTROL)
    spark_signatures.run(FIXTURE, out / "spark", CONTROL)
    return out
