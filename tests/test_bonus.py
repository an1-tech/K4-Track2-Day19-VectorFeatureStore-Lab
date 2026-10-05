"""Memory boundaries and query windows; integration with real Feast is in demo.py."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from bonus.agent import HybridMemoryAgent, chunks, tokens


class ToyEmbedder:
    dim = 2

    def embed(self, texts):
        for text in texts:
            yield np.array([1.0, 0.1 if "cloud" in text else 0.9], dtype=np.float32)


class Store:
    def __init__(self):
        self.latest = {}

    def push(self, name, frame, to):
        assert name == "recent_activity_push"
        row = frame.iloc[0].to_dict()
        self.latest[row["user_id"]] = row

    def get_online_features(self, features, entity_rows):
        user = entity_rows[0]["user_id"]
        row = {"user_id": [user], "topic_affinity": ["cloud"],
               "queries_last_hour": [self.latest[user]["queries_last_hour"]],
               "distinct_topics_24h": [self.latest[user]["distinct_topics_24h"]]}
        return type("Response", (), {"to_dict": lambda self: row})()


def test_chunk_overlap_and_last_chunk():
    text = " ".join(f"w{i}" for i in range(370))
    result = chunks(text)
    assert len(result) == 2
    assert result[0].split()[-30:] == result[1].split()[:30]
    assert result[-1].split()[-1] == "w369"
    assert max(map(lambda s: len(s.split()), result)) <= 200


def test_unicode_tokens_preserve_vietnamese():
    assert tokens("CƠ SỞ, dữ liệu!") == ["cơ", "sở", "dữ", "liệu"]


@pytest.mark.parametrize("mode", ["semantic", "hybrid"])
def test_both_retrievers_isolate_users(mode):
    agent = HybridMemoryAgent(Store(), ToyEmbedder())
    try:
        agent.remember("cloud OUR_PRIVATE", "u_001")
        agent.remember("cloud OTHER_PRIVATE", "u_002")
        result = agent.recall("cloud", "u_001", mode=mode)
        assert "OUR_PRIVATE" in result
        assert "OTHER_PRIVATE" not in result
        assert agent.last_result["features"]["queries_last_hour"] == 1
    finally:
        agent.close()


def test_windows_expire_and_remain_separate_per_user():
    now = [datetime(2026, 10, 5, tzinfo=timezone.utc)]
    store = Store()
    agent = HybridMemoryAgent(store, ToyEmbedder(), clock=lambda: now[0])
    try:
        agent.recall("cloud", "u_001")
        agent.recall("bảo mật", "u_002")
        now[0] += timedelta(hours=1)
        agent.recall("database", "u_001")
        assert store.latest["u_001"]["queries_last_hour"] == 1
        assert store.latest["u_001"]["distinct_topics_24h"] == 2
        assert store.latest["u_002"]["queries_last_hour"] == 1
        now[0] += timedelta(hours=24)
        agent.recall("cloud", "u_001")
        assert store.latest["u_001"]["distinct_topics_24h"] == 1
    finally:
        agent.close()


def test_empty_input_does_not_write_or_push():
    store = Store()
    agent = HybridMemoryAgent(store, ToyEmbedder())
    try:
        with pytest.raises(ValueError):
            agent.remember("   ")
        with pytest.raises(ValueError):
            agent.recall("")
        assert not store.latest
        assert agent.client.count(agent.collection).count == 0
    finally:
        agent.close()
