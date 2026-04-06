import os
import datetime
from typing import Dict, List, Optional, Any

class StorageAdapter:
    def save_run(self, run_id: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class InMemoryStorage(StorageAdapter):
    def __init__(self):
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []

    def save_run(self, run_id: str, data: Dict[str, Any]) -> None:
        if run_id not in self._runs:
            self._order.insert(0, run_id)
        
        # ensure timestamp is present
        if "created_at" not in data:
            data["created_at"] = datetime.datetime.utcnow().isoformat() + "Z"
            
        self._runs[run_id] = data

    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        # _order has newest first
        recent_ids = self._order[:limit]
        return [self._runs[rid] for rid in recent_ids]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._runs.get(run_id)


class FirestoreStorage(StorageAdapter):
    def __init__(self, project_id: str, collection: str = "evaluation_runs"):
        from google.cloud import firestore
        self.db = firestore.Client(project=project_id)
        self.collection = collection

    def save_run(self, run_id: str, data: Dict[str, Any]) -> None:
        if "created_at" not in data:
            data["created_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        self.db.collection(self.collection).document(run_id).set(data)

    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        from google.cloud import firestore
        docs = (
            self.db.collection(self.collection)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.collection(self.collection).document(run_id).get()
        if doc.exists:
            return doc.to_dict()
        return None


def get_storage() -> StorageAdapter:
    """Factory to get the right storage adapter based on env vars."""
    project_id = os.getenv("FIRESTORE_PROJECT_ID")
    if project_id:
        try:
            return FirestoreStorage(project_id)
        except Exception as e:
            print(f"Warning: Failed to initialize Firestore ({e}). Falling back to in-memory.")
            return InMemoryStorage()
    return InMemoryStorage()

# Singleton instance
storage = get_storage()
