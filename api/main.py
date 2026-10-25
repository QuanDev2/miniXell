"""Serve perturbation documents from MongoDB over HTTP.

Each route queries PerturbationRepository and returns the stored document,
validated against a Pydantic response model.

MONGODB_URI selects the server (required). MONGODB_DB selects the database
(default minixell, the database pipeline/load_mongo.py writes). Run with
`uv run --env-file .env uvicorn api.main:app`.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pymongo import AsyncMongoClient

from api.models import Health, Metric, Perturbation, PerturbationSummary, SimilarResponse
from api.repository import PerturbationRepository

DEFAULT_DB = "minixell"  # same database pipeline/load_mongo.py writes
DATASET = "NormanWeissman2019"
SERVER_TIMEOUT_MS = 2_000  # fail fast when MongoDB is down
MAX_LIMIT = 236  # perturbations in the Norman dataset


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Hold one MongoDB client open for the application's lifetime.

    Args:
        app: Application whose state receives the shared repository.

    Yields:
        Control to FastAPI while the application serves requests. The client
        closes on shutdown.

    Raises:
        KeyError: MONGODB_URI is absent from the environment.
    """
    client = AsyncMongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=SERVER_TIMEOUT_MS)
    app.state.repository = PerturbationRepository(client[os.environ.get("MONGODB_DB", DEFAULT_DB)], DATASET)
    yield
    await client.close()


app = FastAPI(title="miniXell", lifespan=lifespan)


def get_repository(request: Request) -> PerturbationRepository:
    """Provide routes with the application's shared repository.

    Args:
        request: Incoming request, used to reach the state set by lifespan.

    Returns:
        Repository bound to the configured database and DATASET.
    """
    return request.app.state.repository


Repository = Annotated[PerturbationRepository, Depends(get_repository)]


@app.get("/health")
async def health(repository: Repository) -> Health:
    """Report whether the service can reach MongoDB.

    Args:
        repository: Shared query layer injected by get_repository.

    Returns:
        Status "ok" when MongoDB answers a ping.

    Raises:
        HTTPException: 503 when MongoDB doesn't answer within SERVER_TIMEOUT_MS.
    """
    if not await repository.ping():
        raise HTTPException(status_code=503, detail="MongoDB unreachable")
    return Health(status="ok")


@app.get("/perturbations")
async def list_perturbations(
    repository: Repository,
    gene: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 50,
) -> list[PerturbationSummary]:
    """List perturbations, optionally only those where a gene is among the top 50 changed genes.

    Args:
        repository: Shared query layer injected by get_repository.
        gene: Exact gene symbol, such as HBZ; omit to list every perturbation.
        limit: Maximum number of results, 1 to MAX_LIMIT.

    Returns:
        Summaries sorted by name. With a gene, each includes that gene's change.
    """
    return [PerturbationSummary(**doc) for doc in await repository.search(gene, limit)]


@app.get("/perturbations/{name}", response_model=Perturbation)
async def get_perturbation(name: str, repository: Repository) -> dict:
    """Return one perturbation's stored summary.

    Args:
        name: Published perturbation label, such as KLF1 or KLF1_BAK1.
        repository: Shared query layer injected by get_repository.

    Returns:
        Document validated by the Perturbation model, with top genes and both
        neighbor lists in rank order.

    Raises:
        HTTPException: 404 when the dataset has no perturbation with this name.
    """
    doc = await repository.get(name)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"perturbation {name!r} not found")
    return doc


@app.get("/perturbations/{name}/similar")
async def get_similar(name: str, repository: Repository, metric: Metric = "edistance") -> SimilarResponse:
    """Return one perturbation's 20 closest matches by one metric.

    Args:
        name: Published perturbation label, such as KLF1.
        repository: Shared query layer injected by get_repository.
        metric: Distance measure: edistance (cell-level, default) or euclidean
            (average-profile).

    Returns:
        Neighbors closest first.

    Raises:
        HTTPException: 404 when the dataset has no perturbation with this name.
    """
    neighbors = await repository.similar(name, metric)
    if neighbors is None:
        raise HTTPException(status_code=404, detail=f"perturbation {name!r} not found")
    return SimilarResponse(name=name, metric=metric, neighbors=neighbors)
