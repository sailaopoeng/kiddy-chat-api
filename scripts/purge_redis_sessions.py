import argparse
import os
import sys
from typing import List

from upstash_redis import Redis

SESSION_INDEX_KEY = "sessions:index"
SESSION_KEY_PATTERN = "session:*"
DELETE_BATCH_SIZE = 100

# Same order as main.py.
REDIS_ENV_PAIRS = [
    ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"),
    ("UPSTASH2_KV_REST_API_URL", "UPSTASH2_KV_REST_API_TOKEN"),
    ("KV_REST_API_URL", "KV_REST_API_TOKEN"),
]


def resolve_redis_config():
    for url_var, token_var in REDIS_ENV_PAIRS:
        url, token = os.getenv(url_var), os.getenv(token_var)
        if url and token:
            return url, token
    return None


def scan_session_keys(redis: Redis) -> List[str]:
    cursor = 0
    keys: List[str] = []

    while True:
        result = redis.scan(cursor, match=SESSION_KEY_PATTERN, count=100)
        cursor = int(result[0])
        keys.extend(result[1])
        if cursor == 0:
            return keys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Purge Kiddy Chat API Redis session data."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete session keys. Without this flag, the script only prints what would be deleted.",
    )
    args = parser.parse_args()

    config = resolve_redis_config()
    if not config:
        names = ", ".join(f"{url}/{token}" for url, token in REDIS_ENV_PAIRS)
        print(f"Missing Redis config. Set one of: {names}.", file=sys.stderr)
        return 1

    url, token = config
    redis = Redis(url=url, token=token, allow_telemetry=False)
    keys = scan_session_keys(redis)

    print(f"Found {len(keys)} session keys and index key '{SESSION_INDEX_KEY}'.")
    if not args.confirm:
        print("Dry run only. Re-run with --confirm to delete session data.")
        return 0

    for index in range(0, len(keys), DELETE_BATCH_SIZE):
        redis.delete(*keys[index:index + DELETE_BATCH_SIZE])
    redis.delete(SESSION_INDEX_KEY)

    print("Redis session data purged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
