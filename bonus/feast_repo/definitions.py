"""Separate bonus registry: batch profile and pushed query activity."""
from datetime import timedelta
from pathlib import Path

from feast import Entity, FeatureView, Field, FileSource, PushSource, ValueType
from feast.types import Int64, String

DATA = Path(__file__).resolve().parent / "data"
user = Entity(name="user", join_keys=["user_id"], value_type=ValueType.STRING)
profile_source = FileSource(name="bonus_profile_source",
                            path=str(DATA / "user_profile.parquet"),
                            timestamp_field="event_timestamp")
activity_batch = FileSource(name="bonus_activity_batch",
                            path=str(DATA / "recent_activity.parquet"),
                            timestamp_field="event_timestamp")
recent_activity_push = PushSource(name="recent_activity_push", batch_source=activity_batch)
user_profile_features = FeatureView(
    name="user_profile_features", entities=[user], ttl=timedelta(days=30), online=True,
    schema=[Field(name="reading_speed_wpm", dtype=Int64),
            Field(name="preferred_language", dtype=String),
            Field(name="topic_affinity", dtype=String)], source=profile_source)
recent_activity_features = FeatureView(
    name="recent_activity_features", entities=[user], ttl=timedelta(hours=1), online=True,
    schema=[Field(name="queries_last_hour", dtype=Int64),
            Field(name="distinct_topics_24h", dtype=Int64)], source=recent_activity_push)
