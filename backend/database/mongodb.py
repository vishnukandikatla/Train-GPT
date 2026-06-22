import os
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
# Note: load_dotenv() is called once in main.py — not repeated here

logger = logging.getLogger("traingpt.database")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/traingpt")

# Local mock persistence file
MOCK_DB_FILE = os.path.join(os.path.dirname(__file__), "mock_db_store.json")

class MockCursor:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        if length is not None:
            return self.data[:length]
        return self.data

class MockCollection:
    def __init__(self, db_instance: 'MockDatabase', name: str):
        self.db = db_instance
        self.name = name

    def _get_data(self) -> List[Dict[str, Any]]:
        return self.db.state.setdefault(self.name, [])

    def _save(self):
        self.db.save()

    async def insert_one(self, document: Dict[str, Any]) -> Any:
        # Simulate Mongo ObjectId if not present
        if "_id" not in document:
            from bson import ObjectId
            document["_id"] = str(ObjectId())
        else:
            document["_id"] = str(document["_id"])
            
        data = self._get_data()
        data.append(document)
        self._save()
        
        class InsertResult:
            inserted_id = document["_id"]
        return InsertResult()

    async def find_one(self, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = self._get_data()
        for doc in data:
            match = True
            for k, v in filter.items():
                # Handle simple filter
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                return doc
        return None

    def find(self, filter: Dict[str, Any]) -> MockCursor:
        data = self._get_data()
        results = []
        for doc in data:
            match = True
            for k, v in filter.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                results.append(doc)
        return MockCursor(results)

    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> Any:
        data = self._get_data()
        target_doc = None
        for doc in data:
            match = True
            for k, v in filter.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                target_doc = doc
                break
                
        class UpdateResult:
            matched_count = 1 if target_doc else 0
            modified_count = 1 if target_doc else 0

        if target_doc:
            if "$set" in update:
                for k, v in update["$set"].items():
                    target_doc[k] = v
            if "$push" in update:
                for k, v in update["$push"].items():
                    if k not in target_doc:
                        target_doc[k] = []
                    target_doc[k].append(v)
            self._save()
            return UpdateResult()
        elif upsert:
            new_doc = filter.copy()
            if "$set" in update:
                for k, v in update["$set"].items():
                    new_doc[k] = v
            await self.insert_one(new_doc)
            return UpdateResult()
            
        return UpdateResult()

    async def delete_one(self, filter: Dict[str, Any]) -> Any:
        data = self._get_data()
        target_idx = -1
        for idx, doc in enumerate(data):
            match = True
            for k, v in filter.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                target_idx = idx
                break
                
        class DeleteResult:
            deleted_count = 0
            
        if target_idx != -1:
            data.pop(target_idx)
            self._save()
            res = DeleteResult()
            res.deleted_count = 1
            return res
        return DeleteResult()

    async def delete_many(self, filter: Dict[str, Any]) -> Any:
        data = self._get_data()
        if not filter:
            # Empty filter means delete all
            removed = len(data)
            data.clear()
            self._save()
        else:
            original_len = len(data)
            remaining = []
            for doc in data:
                match = all(doc.get(k) == v for k, v in filter.items())
                if not match:
                    remaining.append(doc)
            removed = original_len - len(remaining)
            self.db.state[self.name] = remaining
            self._save()

        class DeleteResult:
            deleted_count = removed
        return DeleteResult()

    async def count_documents(self, filter: Dict[str, Any]) -> int:
        cursor = self.find(filter)
        res = await cursor.to_list()
        return len(res)

class MockDatabase:
    def __init__(self):
        self.state: Dict[str, List[Dict[str, Any]]] = {}
        self.load()

    def load(self):
        if os.path.exists(MOCK_DB_FILE):
            try:
                with open(MOCK_DB_FILE, "r") as f:
                    self.state = json.load(f)
                logger.info(f"Loaded mock database state from {MOCK_DB_FILE}")
            except Exception as e:
                logger.error(f"Error loading mock database state: {e}")
                self.state = {}
        else:
            self.state = {}

    def save(self):
        try:
            with open(MOCK_DB_FILE, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving mock database state: {e}")

    def __getattr__(self, name: str) -> MockCollection:
        return MockCollection(self, name)

    def __getitem__(self, name: str) -> MockCollection:
        return MockCollection(self, name)

# Global DB reference initialized to mock by default
db = MockDatabase()
is_mock_db = True
_cached_loop = None

async def init_db():
    global db, is_mock_db, _cached_loop
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from pymongo.errors import ServerSelectionTimeoutError

        logger.info(f"Attempting to connect to MongoDB at: {MONGODB_URI}")
        # Use a short timeout of 2 seconds for server selection
        client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
        # Verify connection by triggering a request
        await client.admin.command('ping')
        
        # Get database name from URI or default
        db_name = MONGODB_URI.split("/")[-1].split("?")[0]
        if not db_name:
            db_name = "traingpt"
        db = client[db_name]
        is_mock_db = False
        try:
            _cached_loop = asyncio.get_running_loop()
        except RuntimeError:
            _cached_loop = None
        logger.info("Connected to MongoDB successfully!")
    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}. Falling back to local file-based database.")
        db = MockDatabase()
        is_mock_db = True
        _cached_loop = None

def get_db():
    global db, _cached_loop
    if not is_mock_db:
        try:
            current_loop = asyncio.get_running_loop()
            if current_loop and current_loop != _cached_loop:
                from motor.motor_asyncio import AsyncIOMotorClient
                db_name = MONGODB_URI.split("/")[-1].split("?")[0]
                if not db_name:
                    db_name = "traingpt"
                client = AsyncIOMotorClient(MONGODB_URI)
                db = client[db_name]
                _cached_loop = current_loop
        except RuntimeError:
            pass
    return db
