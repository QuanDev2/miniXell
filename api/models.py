"""Response shapes for the API; mirror the `perturbations` document schema in ARCHITECTURE.md."""

from pydantic import BaseModel


class Health(BaseModel):
    status: str


class TopGene(BaseModel):
    gene: str
    change: float  # perturbation average minus control average; positive = more active


class Neighbor(BaseModel):
    name: str
    distance: float


class Similar(BaseModel):
    euclidean: list[Neighbor]  # closest first
    edistance: list[Neighbor]  # closest first


class Perturbation(BaseModel):
    dataset: str
    name: str
    target_genes: list[str]
    cell_count: int
    sampled_cell_count: int
    top_genes: list[TopGene]  # largest absolute change first
    similar: Similar
