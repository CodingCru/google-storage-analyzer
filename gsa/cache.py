from pathlib import Path
import diskcache

CACHE_DIR = Path.home() / ".config" / "gsa" / "cache"


def get_cache() -> diskcache.Cache:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return diskcache.Cache(str(CACHE_DIR))
