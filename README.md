# listing-copy-agent

Dávkové generování textů pro e-shop: titulek, popis, meta description a alt text
pro každý produkt — z dodavatelského CSV, s validací limitů a s možností běžet
úplně bez AI (deterministické šablony) nebo s libovolným OpenAI-kompatibilním
endpointem (OpenAI, Azure, Ollama, LM Studio, vLLM…).

## Proč

Ruční psaní popisů u stovek SKU je nejčastější „hluché místo" e-shopu: texty
jsou kopie od dodavatele, chybí jim struktura a nikdo je neaktualizuje. Agent
dělá první verzi, člověk jen schvaluje — a validace nedovolí publikovat text,
který porušuje limity Googlu/Heureky nebo obsahuje nedovolené sliby.

## Použití

```bash
# 1) bez AI — deterministické šablony (běží offline, 0 Kč)
python -m listing_copy generate --in examples/products.csv --out out/copy.csv --provider offline

# 2) s AI (OpenAI-kompatibilní endpoint)
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://api.openai.com/v1
export LISTING_MODEL=gpt-4o-mini
python -m listing_copy generate --in examples/products.csv --out out/copy.csv --provider openai

# 3) validace hotového CSV (např. po ruční úpravě)
python -m listing_copy validate --file out/copy.csv
```

Exit kód `2`, pokud nějaký text neprojde validací — použitelné jako CI gate před
importem do Shoptetu/Shopify.

## Co se validuje

| Pravidlo | Limit |
|---|---|
| `title` | 10–70 znaků, žádné CAPS LOCK, žádné „!!!" |
| `meta_description` | 50–155 znaků |
| `description` | 250–1500 znaků, max. 2 vykřičníky |
| `alt_text` | 5–120 znaků, nesmí být jen název |
| zakázané sliby | „100%", „nejlepší na trhu", „zázrak", „vyléčí", „garantovaně" |

## Architektura

- `providers.py` — `OfflineProvider` (šablony, deterministické) a `OpenAIProvider`
  (jakýkoli OpenAI-kompatibilní `/chat/completions`; bez SDK, jen `urllib`).
- `validate.py` — čisté funkce, vrací seznam chyb; používá se i v testech.
- `cache.py` — SQLite cache podle hashe vstupu, aby se při opakovaném běhu
  neplatilo za stejný produkt dvakrát.
- `cli.py` — dávkový průchod CSV, report kolik bylo vygenerováno / z cache / chyb.

## Formát vstupu

`sku,name,category,attributes,price,currency` — `attributes` oddělené `;`,
např. `materiál: bavlna; barva: béžová; šířka: 160 cm`.

## Formát výstupu

`sku,title,description,meta_description,alt_text,status` (`ok` / `invalid`),
plus `validation_errors` pro rychlou opravu.

## Testy

```bash
python -m unittest discover -s tests -v
```

MIT licencováno.

## Poznámka ke vzniku

Téma vychází z diskusí, kde obchodníci popisují ruční psaní popisů u stovek SKU jako
největší ztrátu času. Kód i šablony jsou vlastní implementace.
