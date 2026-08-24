from app.core.config import get_settings

def traffic() -> int: return get_settings().traffic_cache_ttl_seconds
def provider() -> int: return 60
def route() -> int: return 45
def geocoding() -> int: return 604800
def community() -> int: return 300
