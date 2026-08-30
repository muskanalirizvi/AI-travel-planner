"""MongoDB-backed memory tool for persisting user travel preferences across turns."""

import os
from typing import Optional

from langchain_core.tools import tool
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, PyMongoError

from tools.net import system_certs_ca_file, use_system_certs

_COLLECTION_NAME = "preferences"
_DEFAULT_DB_NAME = "travel_planner"

_collection = None
_init_error: Optional[str] = None


def _get_collection():
    """Lazily connect to MongoDB and return the preferences collection.

    Connects on first use (not import) and caches the result. Raises
    RuntimeError with a clear message if MONGODB_URI is missing or the
    connection fails, so callers can surface a clean error instead of the
    app crashing.
    """
    global _collection, _init_error

    if _collection is not None:
        return _collection
    if _init_error is not None:
        raise RuntimeError(_init_error)

    uri = os.getenv("MONGODB_URI")
    if not uri:
        _init_error = "MONGODB_URI is not set in the environment; the memory tool is unavailable."
        raise RuntimeError(_init_error)

    try:
        client_kwargs = {"serverSelectionTimeoutMS": 5000}
        if use_system_certs():
            client_kwargs["tlsCAFile"] = system_certs_ca_file()
        client = MongoClient(uri, **client_kwargs)
        client.admin.command("ping")
        db_name = os.getenv("MONGODB_DB", "").strip()
        if db_name:
            db = client[db_name]
        else:
            try:
                db = client.get_default_database()
            except ConfigurationError:
                db = client[_DEFAULT_DB_NAME]
        collection = db[_COLLECTION_NAME]
        collection.create_index([("user_id", 1), ("key", 1)], unique=True)
    except PyMongoError as exc:
        _init_error = f"Could not connect to MongoDB: {exc}"
        raise RuntimeError(_init_error) from exc

    _collection = collection
    return _collection


@tool
def save_preference(user_id: str, key: str, value: str) -> str:
    """Save or update a user's travel preference for recall in later turns.

    Use this to remember details like preferred airline, budget range, home
    airport, or past destinations, e.g. save_preference("u123",
    "preferred_airline", "Emirates"). Overwrites any existing value stored
    for the same user_id and key.
    """
    try:
        collection = _get_collection()
        collection.update_one(
            {"user_id": user_id, "key": key},
            {"$set": {"value": value}},
            upsert=True,
        )
    except RuntimeError as exc:
        return f"Error: {exc}"
    except PyMongoError as exc:
        return f"Error saving preference: {exc}"
    return f"Saved preference '{key}' = '{value}' for user '{user_id}'."


@tool
def get_preference(user_id: str, key: str) -> str:
    """Look up a previously saved travel preference for a user.

    Use this to recall details saved earlier with save_preference, e.g.
    get_preference("u123", "preferred_airline"). Returns a clear message if
    nothing has been saved yet for that key.
    """
    try:
        collection = _get_collection()
        doc = collection.find_one({"user_id": user_id, "key": key})
    except RuntimeError as exc:
        return f"Error: {exc}"
    except PyMongoError as exc:
        return f"Error fetching preference: {exc}"

    if doc is None:
        return f"No preference found for '{key}' for user '{user_id}'."
    return f"{key} = {doc['value']}"
