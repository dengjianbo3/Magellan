import json

from app.core.session_store import SessionStore


class _FakeRedis:
    def __init__(self):
        self.values = {}
        self.sorted_sets = {"reports:all": {}}

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, _ttl, value):
        self.values[key] = value

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.values:
                del self.values[key]
                deleted += 1
        return deleted

    def zrem(self, key, member):
        zset = self.sorted_sets.setdefault(key, {})
        if member in zset:
            del zset[member]
            return 1
        return 0


def _build_store(fake_redis: _FakeRedis) -> SessionStore:
    store = SessionStore.__new__(SessionStore)
    store.redis_client = fake_redis
    return store


def test_get_session_filters_by_user_id():
    fake_redis = _FakeRedis()
    store = _build_store(fake_redis)
    fake_redis.values["dd_session:s1"] = json.dumps(
        {
            "session_id": "s1",
            "request": {"user_id": "u1"},
        }
    )

    assert store.get_session("s1", user_id="u1") is not None
    assert store.get_session("s1", user_id="u2") is None


def test_delete_report_rejects_cross_user_delete():
    fake_redis = _FakeRedis()
    store = _build_store(fake_redis)
    fake_redis.values["report:r1"] = json.dumps({"id": "r1", "user_id": "u1"})
    fake_redis.sorted_sets["reports:all"]["r1"] = 123.0

    assert store.delete_report("r1", user_id="u2") is False
    assert "report:r1" in fake_redis.values
    assert "r1" in fake_redis.sorted_sets["reports:all"]

    assert store.delete_report("r1", user_id="u1") is True
    assert "report:r1" not in fake_redis.values
    assert "r1" not in fake_redis.sorted_sets["reports:all"]
