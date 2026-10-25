"""Query perturbation documents in MongoDB for API routes and agent tools.

Documents come from pipeline/load_mongo.py, one per perturbation. Queries
return plain dictionaries so each caller chooses its own validation.
"""

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError


class PerturbationRepository:
    """Read one dataset's perturbation documents.

    Attributes:
        collection: The perturbations collection in the configured database.
        dataset: Published dataset label every query filters on.
    """

    def __init__(self, db: AsyncDatabase, dataset: str) -> None:
        """Bind queries to a database's perturbations collection.

        Args:
            db: Database written by pipeline/load_mongo.py.
            dataset: Published dataset label, such as NormanWeissman2019.
        """
        self.collection = db["perturbations"]
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
