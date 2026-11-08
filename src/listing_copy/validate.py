"""Validation rules for generated copy. Pure functions."""

from __future__ import annotations

from typing import Dict, List

BANNED_PHRASES = (
    "100%",
    "nejlepší na trhu",
    "nejlepší v ČR",
    "zázrak",
    "vyléčí",
    "garantovaně",
    "nikdy nezklame",
)

LIMITS = {
    "title": (10, 70),
    "meta_description": (50, 155),
    "description": (250, 1500),
    "alt_text": (5, 120),
}


def _caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def validate_copy(row: Dict[str, str]) -> List[str]:
    """Return a list of human readable problems; empty list = valid."""
    errors: List[str] = []

    for field, (low, high) in LIMITS.items():
        value = (row.get(field) or "").strip()
        if not value:
            errors.append(f"{field}: chybí")
            continue
        if not (low <= len(value) <= high):
            errors.append(f"{field}: délka {len(value)} znaků, povoleno {low}-{high}")

    title = (row.get("title") or "").strip()
    if title and _caps_ratio(title) > 0.5 and len(title) > 12:
        errors.append("title: příliš mnoho velkých písmen")
    if "!!" in title:
        errors.append("title: vykřičníky")

    description = (row.get("description") or "")
    if description.count("!") > 2:
        errors.append("description: více než 2 vykřičníky")

    joined = " ".join((row.get(k) or "") for k in ("title", "description", "meta_description")).lower()
    for phrase in BANNED_PHRASES:
        if phrase in joined:
            errors.append('zakázaný slib: „' + phrase + '“')

    alt = (row.get("alt_text") or "").strip().lower()
    name = (row.get("name") or "").strip().lower()
    if alt and name and alt == name:
        errors.append("alt_text: opisuje jen název produktu")

    return errors
