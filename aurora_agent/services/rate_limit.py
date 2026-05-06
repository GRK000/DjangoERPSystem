from django.core.cache import cache


def check_rate_limit(user, limit=30, window_seconds=60):
    key = f"agent-rate:{user.id}"
    count = cache.get(key, 0)
    if count >= limit:
        return False
    cache.set(key, count + 1, timeout=window_seconds)
    return True
