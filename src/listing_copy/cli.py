"""CLI: batch CSV in, copy CSV out."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from .cache import CopyCache
from .providers import get_provider
from .validate import validate_copy

FIELDS = ["sku", "title", "description", "meta_description", "alt_text", "status", "validation_errors"]


def generate(args) -> int:
    source = Path(args.input)
    if not source.exists():
        print(f"Vstup nenalezen: {source}", file=sys.stderr)
        return 1

    provider = get_provider(args.provider)
    cache = CopyCache(Path(args.cache)) if args.cache else None
    rows = list(csv.DictReader(source.open(encoding="utf-8-sig")))

    out_rows, generated, cached, failed = [], 0, 0, 0
    for row in rows:
        key = CopyCache.make_key(row, provider.name) if cache else ""
        payload = cache.get(key) if cache else None
        if payload:
            cached += 1
        else:
            try:
                payload = provider.generate(row)
                generated += 1
                if cache:
                    cache.put(key, payload)
            except Exception as exc:  # noqa: BLE001 - report, keep the batch alive
                failed += 1
                out_rows.append(
                    {
                        "sku": row.get("sku", ""),
                        "title": "",
                        "description": "",
                        "meta_description": "",
                        "alt_text": "",
                        "status": "error",
                        "validation_errors": str(exc)[:200],
                    }
                )
                continue

        payload["name"] = row.get("name", "")
        errors = validate_copy(payload)
        out_rows.append(
            {
                "sku": payload.get("sku", ""),
                "title": payload.get("title", ""),
                "description": payload.get("description", ""),
                "meta_description": payload.get("meta_description", ""),
                "alt_text": payload.get("alt_text", ""),
                "status": "ok" if not errors else "invalid",
                "validation_errors": "; ".join(errors),
            }
        )

    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)

    if cache:
        cache.close()

    invalid = sum(1 for r in out_rows if r["status"] != "ok")
    print(f"Hotovo: {len(out_rows)} produktů | nově {generated} | z cache {cached} | chyb {failed} | nevalidních {invalid}")
    print(f"Výstup: {target}")
    return 2 if invalid else 0


def validate_file(args) -> int:
    path = Path(args.file)
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    problems = 0
    for row in rows:
        errors = validate_copy(row)
        if errors:
            problems += 1
            print(f"[{row.get('sku', '?')}] " + "; ".join(errors))
    print(f"Zkontrolováno {len(rows)} řádků, problémů: {problems}")
    return 2 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="listing-copy", description="Dávkové texty pro e-shop")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Vygenerovat texty z CSV")
    gen.add_argument("--in", dest="input", required=True)
    gen.add_argument("--out", dest="output", required=True)
    gen.add_argument("--provider", default="offline", choices=["offline", "openai"])
    gen.add_argument("--cache", default=".listing_cache.sqlite", help="SQLite cache ('' vypne)")
    gen.set_defaults(func=generate)

    val = sub.add_parser("validate", help="Zkontrolovat hotové CSV")
    val.add_argument("--file", required=True)
    val.set_defaults(func=validate_file)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
