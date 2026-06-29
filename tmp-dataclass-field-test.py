from dataclasses import dataclass, field
from typing import Any
@dataclass(frozen=True)
class DiscoveryCandidate:
    tags: dict[str, Any] = field(default_factory=dict)
