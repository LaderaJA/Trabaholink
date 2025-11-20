"""Typed structures for verification pipeline results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from users.models import CustomUser


@dataclass
class VerificationResult:
    """Outcome payload for the verification pipeline."""

    user: CustomUser
    status: str
    similarity_score: Optional[float] = None
    extracted_data: Dict[str, str] = field(default_factory=dict)
    verification_score: Optional[float] = None
    notes: str = ""
