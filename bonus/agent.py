"""Vietnamese hybrid memory POC: user-scoped BM25 + vector + Feast context."""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pandas as pd
from feast.data_source import PushMode
from qdrant_client import QdrantClient, models
from rank_bm25 import BM25Okapi

from app.embeddings import Embedder


def tokens(text: str) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold())


def chunks(text: str, size: int = 200, overlap: int = 30) -> list[str]:
    if not 0 <= overlap < size:
        raise ValueError("Require 0 <= overlap < size")
    words = text.split()
    result = []
    for start in range(0, len(words), size - overlap):
        result.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
    return result


class HybridMemoryAgent:
    """Keep each user's memories separate and return context without an LLM call."""

    def __init__(self, feature_store, embedder=None, clock=None):
        self.store = feature_store
        self.embedder = embedder or Embedder("fastembed")
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.client = QdrantClient(":memory:")
        self.collection = "bonus_user_memories"
        self.client.create_collection(
            self.collection,
            vectors_config=models.VectorParams(size=self.embedder.dim,
                                                distance=models.Distance.COSINE),
        )
        self.records = defaultdict(list)
        self.events = defaultdict(deque)
        self.last_result = {}

    @staticmethod
    def _validate(text, user_id):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text must be non-empty")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be non-empty")

    def remember(self, text: str, user_id: str = "u_001") -> None:
        self._validate(text, user_id)
        pieces = chunks(text)
        vectors = list(self.embedder.embed(pieces))
        payloads = [{"doc_id": str(uuid4()), "user_id": user_id, "text": part,
                     "created_at": self.clock().isoformat()} for part in pieces]
        self.client.upsert(self.collection, points=[
            models.PointStruct(id=p["doc_id"], vector=v.tolist(), payload=p)
            for p, v in zip(payloads, vectors)
        ], wait=True)
        self.records[user_id].extend(payloads)

    def _record_query(self, query, user_id):
        from app.agent import RuleBasedPlanner
        now = self.clock()
        history = self.events[user_id]
        topic = RuleBasedPlanner.detect_topic(query) or "other"
        history.append((now, topic))
        while history and history[0][0] <= now - timedelta(hours=24):
            history.popleft()
        row = {"user_id": user_id, "event_timestamp": now,
               "queries_last_hour": sum(ts > now - timedelta(hours=1) for ts, _ in history),
               "distinct_topics_24h": len({t for _, t in history})}
        self.store.push("recent_activity_push", pd.DataFrame([row]), to=PushMode.ONLINE)

    def recall(self, query: str, user_id: str = "u_001", *, mode="hybrid", top_k=3) -> str:
        self._validate(query, user_id)
        if mode not in ("semantic", "hybrid") or not 1 <= top_k <= 10:
            raise ValueError("mode must be semantic/hybrid and top_k must be 1..10")
        self._record_query(query, user_id)
        features = self.store.get_online_features(features=[
            "user_profile_features:reading_speed_wpm",
            "user_profile_features:preferred_language",
            "user_profile_features:topic_affinity",
            "recent_activity_features:queries_last_hour",
            "recent_activity_features:distinct_topics_24h",
        ], entity_rows=[{"user_id": user_id}]).to_dict()
        profile = {k: v[0] for k, v in features.items()}
        depth = max(50, top_k * 5) if mode == "hybrid" else top_k
        qfilter = models.Filter(must=[models.FieldCondition(
            key="user_id", match=models.MatchValue(value=user_id))])
        query_vector = next(self.embedder.embed([query])).tolist()
        hits = self.client.query_points(self.collection, query=query_vector,
                                        query_filter=qfilter, limit=depth).points
        semantic = [p.payload["doc_id"] for p in hits]
        own = self.records[user_id]
        by_id = {p["doc_id"]: p for p in own}
        ranked = semantic
        if mode == "hybrid" and own:
            corpus = [tokens(p["text"]) for p in own]
            if all(corpus):
                scores = BM25Okapi(corpus).get_scores(tokens(query))
                keyword = [own[i]["doc_id"] for i in sorted(
                    range(len(own)), key=lambda i: -scores[i])[:depth] if scores[i] > 0]
                fused = defaultdict(float)
                for ranking in (keyword, semantic):
                    for rank, doc_id in enumerate(ranking, 1):
                        fused[doc_id] += 1.0 / (60 + rank)
                ranked = sorted(fused, key=lambda doc_id: -fused[doc_id])
        selected = [by_id[doc_id] for doc_id in ranked[:top_k]]
        assert all(p["user_id"] == user_id for p in selected)
        self.last_result = {"user_id": user_id, "mode": mode,
                            "features": profile, "memories": selected}
        return json.dumps(self.last_result, ensure_ascii=False, indent=2)

    def close(self):
        self.client.close()
