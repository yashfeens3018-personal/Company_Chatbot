"""
Semantic cache for RAG (handbook) answers ONLY. Put this file next to chat.py.

- Key   : the standalone `rag_query` produced by intent classification.
- Value : the final answer text.
- Store : its own Chroma collection in its own directory, so it never touches
          the handbook index and can be wiped with `rm -rf rag_cache_db`.
- Version: every entry is tagged with a hash of (ingestion manifest + answer model
          + prompt version). If the handbook, the ingestion config, the model or the
          prompt changes, the hash changes and old entries can never be matched.
- Safety: every public function fails safe. On any error the caller just sees a miss.
"""
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
logger = logging.getLogger(__name__)

# ingestion index k liye (only used to read the manifest for versioning) 
INDEX_DIR = "./chroma_langchain_db"
MANIFEST_PATH = os.path.join(INDEX_DIR, "manifest.json")

# ---- cache embedding model ----------------------------------------------------
# Deliberately separate from the retrieval model in vector_db.py. Chosen with
# tune_cache_threshold.py: bge-base separated "same question" from "same topic" best.
# Changing it changes the vector size, so delete ./rag_cache_db when you do.
CACHE_EMBED_MODEL = "BAAI/bge-base-en-v1.5"


CACHE_DIR = "./rag_cache_db"
COLLECTION = "rag_cache"
SIMILARITY_THRESHOLD = 0.92      # from tune_cache_threshold.py with bge-base: 0 false hits at >=0.90 therefore pciked this threshold
TTL_SECONDS = 7 * 24 * 3600      # safety net on top of versioning

# ---- bump these when cached answers would change ------------------------------
ANSWER_MODEL = "gemini-2.5-flash"   #same as chat.py
PROMPT_VERSION = 1                  #depends on the changes of final prompt version


embeddings = HuggingFaceEmbeddings(
    model_name=CACHE_EMBED_MODEL,
    encode_kwargs={"normalize_embeddings": True},
)

try:
    _store = Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings,
        persist_directory=CACHE_DIR,
        collection_metadata={"hnsw:space": "cosine"},
    )
except Exception:
    logger.exception("RAG cache disabled: could not open the Chroma cache store")
    _store = None


@dataclass
class CacheHit:
    answer: str
    score: float
    matched_query: str


_version_memo = {"mtime": None, "value": None}


def get_cache_version() -> str | None:
    try:
        mtime = os.path.getmtime(MANIFEST_PATH)
        if _version_memo["mtime"] != mtime:
            with open(MANIFEST_PATH, encoding="utf-8") as f:
                manifest = json.load(f)
            payload = json.dumps(
                {"manifest": manifest, "model": ANSWER_MODEL, "prompt": PROMPT_VERSION, "embed": CACHE_EMBED_MODEL},
                sort_keys=True,
            )
            _version_memo["value"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
            _version_memo["mtime"] = mtime
        return _version_memo["value"]
    except (OSError, json.JSONDecodeError):
        logger.warning("Cache version unknown (manifest missing/unreadable); cache bypassed")
        return None



def best_match(query: str) -> CacheHit | None:
    version = get_cache_version()
    if _store is None or not version or not query or not query.strip():
        return None
    try:
        results = _store.similarity_search_with_score(
            query,
            k=1,
            filter={"$and": [
                {"kb_version": version},
                {"created_at": {"$gt": time.time() - TTL_SECONDS}},
            ]},
        )
    except Exception:
        logger.exception("Cache lookup failed")
        return None
    if not results:
        return None
    doc, distance = results[0]
    return CacheHit(answer=doc.metadata["answer"], score=1.0 - float(distance), matched_query=doc.page_content)


def lookup(query: str, threshold: float = SIMILARITY_THRESHOLD) -> CacheHit | None:
    hit = best_match(query)
    return hit if hit and hit.score >= threshold else None


def store(query: str, answer: str) -> None:
    version = get_cache_version()
    if _store is None or not version or not query or not query.strip() or not answer or not answer.strip():
        return
    try:
        _store.add_texts(
            texts=[query],  # the embedded text is the QUESTION
            metadatas=[{"answer": answer, "kb_version": version, "created_at": time.time()}],
            ids=[str(uuid.uuid4())],
        )
    except Exception:
        logger.exception("Cache store failed")


def purge_stale() -> None:
    """Delete entries from older versions and expired entries. Call once at app startup."""
    version = get_cache_version()
    if _store is None or not version:
        return
    try:
        _store.delete(where={"kb_version": {"$ne": version}})
        _store.delete(where={"created_at": {"$lt": time.time() - TTL_SECONDS}})
    except Exception:
        logger.exception("Cache purge failed")