from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import hashlib

@dataclass
class RawJobOffer:
    """Structure commune pour toutes les plateformes"""
    title: str
    company_name: str
    location: str
    description: str
    source_url: str
    source_platform: str
    contract_type: str = "stage"
    duration_months: Optional[int] = None
    posted_at: Optional[datetime] = None

    def compute_hash(self) -> str:
        """Hash unique pour déduplication"""
        raw = f"{self.title.lower().strip()}{self.company_name.lower().strip()}{self.source_platform}"
        return hashlib.sha256(raw.encode()).hexdigest()