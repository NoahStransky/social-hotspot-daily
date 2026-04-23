"""Deduplication engine using URL and title similarity."""
import hashlib
from typing import List, Set
from difflib import SequenceMatcher
from collectors.base import NewsItem


class Deduplicator:
    """Remove duplicate and near-duplicate news items."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.seen_urls: Set[str] = set()
        self.seen_titles: List[str] = []
        self.threshold = similarity_threshold
    
    def deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        unique = []
        
        for item in items:
            # Exact URL dedup
            url_hash = hashlib.md5(item.url.encode()).hexdigest()
            if url_hash in self.seen_urls:
                continue
            
            # Title similarity dedup
            if self._is_similar_title(item.title):
                continue
            
            self.seen_urls.add(url_hash)
            self.seen_titles.append(item.title)
            unique.append(item)
        
        return unique
    
    def _is_similar_title(self, title: str) -> bool:
        title_lower = title.lower()
        for seen in self.seen_titles:
            ratio = SequenceMatcher(None, title_lower, seen.lower()).ratio()
            if ratio >= self.threshold:
                return True
        return False
