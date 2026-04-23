"""Base collector interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import hashlib


@dataclass
class NewsItem:
    title: str
    url: str
    source: str  # e.g. "twitter", "reddit"
    source_name: str  # e.g. "@ylecun", "r/technology"
    hot_score: float = 0.0
    category: str = "general"
    language: str = "en"
    summary: str = ""
    collected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    raw_data: dict = field(default_factory=dict)
    
    @property
    def id(self) -> str:
        """Generate unique ID based on URL."""
        return hashlib.md5(self.url.encode()).hexdigest()[:12]


class BaseCollector(ABC):
    """Abstract base class for all news collectors."""
    
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("enabled", False)
        self.name = self.__class__.__name__.replace("Collector", "").lower()
    
    @abstractmethod
    def collect(self) -> List[NewsItem]:
        """Fetch news items from the source."""
        pass
    
    def is_available(self) -> bool:
        """Check if collector is properly configured."""
        return self.enabled
