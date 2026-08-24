from dataclasses import dataclass

@dataclass(slots=True)
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    writes: int = 0
    deletes: int = 0
