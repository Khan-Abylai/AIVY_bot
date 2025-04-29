#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced memory module with **recency‑boost** post‑ranking.
• Stores user utterances in Qdrant with timestamp payload
• At recall — ranks by similarity *plus* slight bonus for freshness
"""

import time
import logging
from typing import List

from tenacity import retry, stop_after_attempt, wait_exponential
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI

from config import QDRANT_URL, QDRANT_API_KEY, OPENAI_API_KEY

# ───────────────────────────  CONSTANTS  ───────────────────────────
COLLECTION = "aivi_psybot_memory"
EMBED_MODEL = "text-embedding-ada-002"
VECTOR_SIZE = 1536
RECENCY_ALPHA = 0.10  # weight for timestamp boost in ranking

# ───────────────────────────  LOGGING  ────────────────────────────
glogger = logging.getLogger(__name__)
glogger.setLevel(logging.INFO)

# ───────────────────────────  CLIENTS  ────────────────────────────
emb_client = OpenAI(api_key=OPENAI_API_KEY)

qdrant = QdrantClient(
    url=QDRANT_URL,
    prefer_grpc=False,
    api_key=QDRANT_API_KEY or None,
    timeout=5.0,
)

# ─────────────────────────  COLLECTION  ───────────────────────────

def create_collection() -> None:
    """Create or recreate the Qdrant collection for memory storage."""
    try:
        qdrant.recreate_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )
        glogger.info("Collection '%s' is ready.", COLLECTION)
    except Exception as e:
        glogger.error("Failed to create collection: %s", e)

# ─────────────────────────  EMBEDDINGS  ───────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def embed(text: str) -> List[float]:
    """Generate embedding vector for a given text."""
    if not text:
        return []
    resp = emb_client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding

# ─────────────────────────  WRITE MEMORY  ─────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def add_to_memory(user_id: str, text: str) -> None:
    """Persist a user utterance with its vector and timestamp."""
    if not user_id or not text:
        glogger.warning("Cannot add empty memory entry.")
        return

    vec = embed(text)
    if not vec:
        glogger.warning("Empty embedding, skipping memory write.")
        return

    point = models.PointStruct(
        id=int(time.time() * 1000),
        vector=vec,
        payload={"user": user_id, "text": text, "ts": time.time()},
    )
    try:
        qdrant.upsert(collection_name=COLLECTION, points=[point])
        glogger.debug("Memory stored for user %s", user_id)
    except Exception as e:
        glogger.error("Failed to upsert memory: %s", e)

# ─────────────────────────  READ MEMORY  ──────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def recall(user_id: str, query: str, k: int = 10) -> List[str]:
    """Retrieve up to *k* most relevant memories for the user with recency boost."""
    if not user_id:
        glogger.warning("No user_id provided for recall.")
        return []

    vec = embed(query)
    if not vec:
        return []

    try:
        hits = qdrant.search(
            collection_name=COLLECTION,
            query_vector=vec,
            limit=k * 3,  # fetch extra for better re‑ranking
            with_payload=True,
        )
        now = time.time()
        rescored = []
        for h in hits:
            if h.payload.get("user") != user_id:
                continue
            # similarity score (0..1), higher is better
            sim = h.score
            # recency bonus: newer → larger bonus (ts closer to now)
            recency_bonus = RECENCY_ALPHA * (h.payload.get("ts", 0) / now)
            rescored.append((sim + recency_bonus, h.payload.get("text", "")))

        # sort by combined score desc and return top‑k texts
        rescored.sort(key=lambda t: t[0], reverse=True)
        seen = set()
        unique = []
        for score, txt in rescored:
            if txt not in seen:
                seen.add(txt)
                unique.append((score, txt))
            if len(unique) >= k:
                break
        return [txt for _, txt in unique]
    except Exception as e:
        glogger.error("Memory search failed: %s", e)
        return []
