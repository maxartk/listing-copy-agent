"""Copy providers: deterministic offline templates and OpenAI-compatible API."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Dict, List

SYSTEM_PROMPT = (
    "Jsi copywriter českého e-shopu. Piš věcně, bez superlativů a bez vymyšlených "
    "parametrů. Nepoužívej slova jako 100%, nejlepší na trhu, zázrak. "
    "Odpověz pouze JSON objektem s klíči title, description, meta_description, alt_text."
)


def parse_attributes(raw: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"[;|]", raw or "") if p.strip()]
    return parts


def _bullets(attributes: List[str]) -> List[str]:
    bullets = []
    for item in attributes:
        if ":" in item:
            key, value = item.split(":", 1)
            bullets.append(f"- {key.strip().capitalize()}: {value.strip()}")
        else:
            bullets.append(f"- {item}")
    return bullets


class OfflineProvider:
    """Deterministic Czech copy built from the product attributes."""

    name = "offline"

    def generate(self, row: Dict[str, str]) -> Dict[str, str]:
        name = (row.get("name") or row.get("sku") or "Produkt").strip()
        category = (row.get("category") or "").strip()
        attributes = parse_attributes(row.get("attributes", ""))
        bullets = _bullets(attributes)

        title = name if len(name) <= 70 else name[:67].rstrip() + "…"

        intro_parts = [f"{name}"]
        if category:
            intro_parts.append(f"z kategorie {category.lower()}")
        intro = " ".join(intro_parts) + "."
        body = [
            intro,
            "",
            "Hlavní parametry:",
            *(bullets or ["- parametry doplníme po dodání od výrobce"]),
            "",
            "Zboží expedujeme z českého skladu. Pokud si nejste jistí výběrem, "
            "napište nám rozměry a my poradíme s vhodnou variantou.",
        ]
        description = "\n".join(body).strip()

        meta_bits = [name]
        if category:
            meta_bits.append(category.lower())
        if attributes:
            meta_bits.append(attributes[0])
        meta = " · ".join(meta_bits) + " — skladem, rychlé dodání."
        if len(meta) > 155:
            meta = meta[:152].rstrip(" ,·-") + "…"

        alt = f"{name}" + (f", {category.lower()}" if category else "")
        alt = alt[:120]

        return {
            "sku": row.get("sku", ""),
            "name": name,
            "title": title,
            "description": description,
            "meta_description": meta,
            "alt_text": alt,
        }


class OpenAIProvider:
    """Any OpenAI-compatible /chat/completions endpoint."""

    name = "openai"

    def __init__(self, model: str = None, base_url: str = None, api_key: str = None, timeout: int = 60):
        self.model = model or os.environ.get("LISTING_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.timeout = timeout

    def _prompt(self, row: Dict[str, str]) -> str:
        return (
            f"Produkt: {row.get('name')}\n"
            f"Kategorie: {row.get('category')}\n"
            f"Parametry: {row.get('attributes')}\n"
            f"Cena: {row.get('price')} {row.get('currency', 'CZK')}\n"
            "Napiš titulek do 70 znaků, popis 400-900 znaků, meta description do 155 znaků "
            "a alt text do 120 znaků."
        )

    def generate(self, row: Dict[str, str]) -> Dict[str, str]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY není nastaven")

        payload = {
            "model": self.model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._prompt(row)},
            ],
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"API {exc.code}: {exc.read()[:200]!r}") from exc

        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return {
            "sku": row.get("sku", ""),
            "name": row.get("name", ""),
            "title": parsed.get("title", ""),
            "description": parsed.get("description", ""),
            "meta_description": parsed.get("meta_description", ""),
            "alt_text": parsed.get("alt_text", ""),
        }


def get_provider(name: str):
    if name == "offline":
        return OfflineProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"Neznámý provider: {name}")
