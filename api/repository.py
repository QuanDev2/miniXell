"""Query perturbation and gene documents in MongoDB for API routes and agent tools.

Perturbation documents come from pipeline/load_mongo.py, gene descriptions from
pipeline/fetch_genes.py. Queries return plain dictionaries so each caller
chooses its own validation.
"""

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError


class PerturbationRepository:
    """Read one dataset's perturbation documents.

    Attributes:
        collection: The perturbations collection in the configured database.
        genes: The genes collection holding public gene descriptions.
        dataset: Published dataset label every perturbation query filters on.
    """

    def __init__(self, db: AsyncDatabase, dataset: str) -> None:
        """Bind queries to a database's perturbations and genes collections.

        Args:
            db: Database written by pipeline/load_mongo.py and fetch_genes.py.
            dataset: Published dataset label, such as NormanWeissman2019.
        """
        self.collection = db["perturbations"]
        self.genes = db["genes"]
        self.dataset = dataset

    async def ping(self) -> bool:
        """Check whether MongoDB answers.

        Returns:
            True if the server responds within the client's server-selection
            timeout; False on any driver error.
        """
        try:
            await self.collection.database.command("ping")
        except PyMongoError:
            return False
        return True

    async def get(self, name: str) -> dict | None:
        """Fetch one perturbation's document by name.

        Args:
            name: Published perturbation label, such as KLF1 or KLF1_BAK1.

        Returns:
            Stored document without MongoDB's _id, or None if the dataset has
            no perturbation with this name.
        """
        return await self.collection.find_one({"dataset": self.dataset, "name": name}, {"_id": 0})

    async def search(self, gene: str | None, limit: int) -> list[dict]:
        """List perturbation summaries, optionally only those where a gene is a top gene.

        Args:
            gene: Exact gene symbol, such as HBZ, to match against each
                document's top genes; None lists every perturbation.
            limit: Maximum number of summaries to return.

        Returns:
            Summaries sorted by name with name, target_genes, and cell_count.
            With a gene, each also has gene_change, that gene's change in the
            perturbation.
        """
        query = {"dataset": self.dataset}
        projection = {"_id": 0, "name": 1, "target_genes": 1, "cell_count": 1}
        if gene is not None:
            query["top_genes.gene"] = gene
            projection["top_genes.$"] = 1  # only the matched array element
        docs = await self.collection.find(query, projection).sort("name", 1).limit(limit).to_list()
        for doc in docs:
            if matched := doc.pop("top_genes", None):
                doc["gene_change"] = matched[0]["change"]
        return docs

    async def similar(self, name: str, metric: str) -> list[dict] | None:
        """Fetch one perturbation's closest matches by one metric.

        Args:
            name: Published perturbation label, such as KLF1.
            metric: Key of the document's similar object: euclidean or edistance.

        Returns:
            Neighbors as {name, distance}, closest first, or None if the dataset
            has no perturbation with this name.
        """
        doc = await self.collection.find_one(
            {"dataset": self.dataset, "name": name}, {"_id": 0, f"similar.{metric}": 1}
        )
        return None if doc is None else doc["similar"][metric]

    async def descriptions(self, symbols: list[str]) -> dict[str, dict]:
        """Fetch stored descriptions for a list of genes.

        Args:
            symbols: Gene names as the dataset spells them, such as HBG1.

        Returns:
            Each stored symbol mapped to its document without _id. Symbols
            never fetched are absent; fetched ones may have a null summary.
        """
        cursor = self.genes.find({"symbol": {"$in": symbols}}, {"_id": 0})
        return {doc["symbol"]: doc async for doc in cursor}
