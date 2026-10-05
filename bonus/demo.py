"""Run the five required queries plus a cross-user isolation check; no API key."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")

import pandas as pd
from feast import FeatureStore

from bonus.agent import HybridMemoryAgent
from bonus.feast_repo import definitions as definitions


def prepare_store() -> FeatureStore:
    """Seed synthetic profiles or use NB4's existing profiles, in a new project."""
    definitions.DATA.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc) - timedelta(seconds=1)
    core_source = ROOT / "app" / "feast_repo" / "data" / "user_profile.parquet"
    if core_source.exists():
        profiles = pd.read_parquet(core_source)
    else:
        profiles = pd.DataFrame({
            "user_id": ["u_001", "u_002"], "reading_speed_wpm": [187, 194],
            "preferred_language": ["vi", "vi"], "topic_affinity": ["cloud", "security"],
            "event_timestamp": [now, now],
        })
    profiles.to_parquet(definitions.DATA / "user_profile.parquet", index=False)
    pd.DataFrame({"user_id": profiles.user_id, "queries_last_hour": 0,
                  "distinct_topics_24h": 0, "event_timestamp": now}).to_parquet(
                      definitions.DATA / "recent_activity.parquet", index=False)
    store = FeatureStore(repo_path=str(ROOT / "bonus" / "feast_repo"))
    store.apply([definitions.user, definitions.user_profile_features,
                 definitions.recent_activity_features])
    store.materialize(now - timedelta(days=30), datetime.now(timezone.utc))
    return store


def main() -> None:
    store = prepare_store()
    agent = HybridMemoryAgent(store)
    memories = [
        "Tôi đã đọc hướng dẫn Kubernetes: cấu hình deployment, pod và autoscaling để tự động mở rộng hạ tầng theo lưu lượng.",
        "Tôi quan tâm cloud security: IAM theo least privilege, mã hóa dữ liệu và giới hạn quyền truy cập tài liệu.",
        "Tài liệu tối ưu chi phí cloud giới thiệu spot instance, ngân sách và theo dõi mức sử dụng tài nguyên.",
        "Gần đây tôi đọc về CDN và cân bằng tải giữa nhiều region để giảm độ trễ.",
        "Tôi đã lưu ghi chú PostgreSQL: chỉ mục B-tree giúp tối ưu truy vấn cơ sở dữ liệu.",
        "Tài liệu Terraform giải thích cách quản lý hạ tầng bằng code và kiểm tra thay đổi trước khi triển khai.",
    ]
    for memory in memories:
        agent.remember(memory)
    agent.remember("PRIVATE_U002: ghi chú riêng của người dùng thứ hai.", "u_002")
    questions = [
        ("Tôi đã đọc gì về Kubernetes?", "semantic"),
        ("Recommend đọc gì tiếp", "hybrid"),
        ("Tôi đang quan tâm gì gần đây?", "hybrid"),
        ("Tài liệu về tự động mở rộng hạ tầng?", "semantic"),
        ("Cho tôi summary cloud security", "hybrid"),
    ]
    for i, (question, mode) in enumerate(questions, 1):
        print(f"\nQUERY {i}: {question}")
        context = agent.recall(question, mode=mode)
        print(context)
        assert "PRIVATE_U002" not in context
        assert agent.last_result["features"]["queries_last_hour"] == i
        assert agent.last_result["features"]["topic_affinity"] == "cloud"
        assert agent.last_result["memories"]
    print("\nPASS: 5 contexts, fresh Feast activity and no cross-user memories")
    agent.close()


if __name__ == "__main__":
    main()
