# SLAI — Prompt & Guardrail Documentation

**Repository:** [github.com/basketsavings/slai](https://github.com/basketsavings/slai)  
**Model:** `gemini-2.0-flash` (Google Gemini) for all LLM calls  
**Last Updated:** March 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Processing Pipeline](#processing-pipeline)
3. [Prompt 1 — Parser Agent](#prompt-1--parser-agent)
4. [Prompt 2 — Normalizer Agent](#prompt-2--normalizer-agent)
5. [Prompt 3 — Recipe Extraction (by Name)](#prompt-3--recipe-extraction-by-name)
6. [Prompt 4 — Recipe Extraction (from URL)](#prompt-4--recipe-extraction-from-url)
7. [Guardrails & Confidence Scoring](#guardrails--confidence-scoring)
8. [Brand Logic Guardrail](#brand-logic-guardrail)
9. [Safe Fallback Behavior](#safe-fallback-behavior)
10. [Output Contract Enforcement](#output-contract-enforcement)

---

## Overview

SLAI uses **two LLM agents** in sequence to convert messy grocery text into clean structured data, followed by **deterministic (non-LLM) guardrails** to prevent hallucinations.

| Layer | Type | Responsibility |
|-------|------|----------------|
| Parser Agent | LLM (Gemini) | Split raw text into individual items; remove conversational noise |
| Normalizer Agent | LLM (Gemini) | Extract structure from each item (name, quantity, brand) |
| Autocomplete API | External API | Only authoritative source for real product SKUs and names |
| Product Resolver | Deterministic code | Confidence scoring, brand logic, safe fallbacks |

**Core principle:** LLMs handle language understanding; code and APIs decide on products. The LLM is never allowed to invent a SKU or product name.

---

## Processing Pipeline

```
Raw User Input (e.g. "get some chicken, like chicken breast, and kerrygold butter 2")
         │
         ▼
┌────────────────────────┐
│   Parser Agent (LLM)   │  ← PROMPT 1
│   Temperature: 0       │
└────────────────────────┘
         │
         │  ["chicken breast", "Kerrygold butter 2"]
         ▼
┌────────────────────────┐
│ Normalizer Agent (LLM) │  ← PROMPT 2
│   Temperature: 0       │  (single batch call for all items)
└────────────────────────┘
         │
         │  NormalizedItem objects with has_brand, quantity, modifiers
         ▼
┌────────────────────────┐
│  Autocomplete API      │  (parallel HTTP calls, no LLM)
│  BasketSavings         │
└────────────────────────┘
         │
         │  Up to 20 product suggestions per item
         ▼
┌────────────────────────┐
│  Product Resolver      │  ← GUARDRAILS (deterministic)
│  Confidence Scoring    │
└────────────────────────┘
         │
         ▼
    StructuredItem[]  (final JSON output)
```

---

## Prompt 1 — Parser Agent

**File:** [`app/agents/parser.py`](https://github.com/basketsavings/slai/blob/main/app/agents/parser.py)  
**Called by:** `parse_and_normalize()` in `app/api/routes.py`  
**Temperature:** `0` (fully deterministic)

### Purpose

Splits a single blob of raw conversational grocery text into a list of individual item strings. Removes filler words, greetings, and deduplications — when a user clarifies a vague item, only the final specific version is kept.

### Full Prompt

```
You are a grocery list parser that extracts individual products from CONVERSATIONAL input.

YOUR JOB:
Extract ONLY unique grocery products. Remove ALL conversational noise and duplicates.

NOISE TO REMOVE (never include as items):
- Greetings/closings: "Okay", "Let's make", "Thanks", "That's it", "Oh actually"
- Fillers: "and", "then", "also", "um", "like", "maybe", "I think", "some"
- Instructions: "Let's get", "Get me", "I need", "for that get", "add"

CLARIFICATION HANDLING (CRITICAL):
When user clarifies or specifies a vague item, ONLY keep the FINAL specific version:
- "some chicken, like chicken breast" → "chicken breast" (NOT "chicken" AND "chicken breast")
- "onions, maybe like a red onion" → "red onion" (NOT "onions" AND "red onion")
- "mushrooms, the bella mushroom, portobello, whatever" → "portobello mushroom" (ONLY final one)
- "yogurt, and for that, get La Farmier yogurt mango flavor" → "La Farmier mango yogurt" (ONLY the specific)
- "get some X, and for that, get Y" means Y replaces X - output ONLY Y

WHAT TO EXTRACT:
- Brand + Attribute + Product as ONE item (Häagen-Dazs vanilla bean ice cream)
- **ALT HANDLING (CRITICAL)**: If user gives **alternatives** with **or** (e.g. "Ground beef 80/20 or 85/15"), output **one** string with their **full** wording — do not drop alternatives. Downstream normalization will use base product **Ground beef** and notes **80/20 or 85/15**. If user gives **only one** spec and **no** "or" (e.g. "Ground beef 80/20"), output that **entire** phrase as one item so it stays the full product name.
- PRESERVE brands exactly (Kerrygold, La Farmier, Haagen-Dazs)
- PRESERVE flavor/variety (Cool Ranch, mango, vanilla bean)
- Attach item **count** at the **start** of the string ("get two of those" → **"2 …"** before the product name, not after)
- PRESERVE size/weight; in output strings use a **space** between number and unit (**8 oz**, **2 lb**). Users may type "8oz" — normalize spacing in your outputs

DEDUPLICATION:
- If user says generic then specific, ONLY output the specific
- No duplicates - each unique product once

OUTPUT FORMAT:
Return a JSON array of strings, one unique product per item.
```

### Few-Shot Examples in Prompt

| Input | Output |
|-------|--------|
| `"Häagen-Dazs vanilla bean ice cream, Cool Ranch Doritos, Kerrygold butter, some eggs."` | `["Häagen-Dazs vanilla bean ice cream", "Cool Ranch Doritos", "Kerrygold butter", "eggs"]` |
| `"yogurt, and for that, get the La Farmier yogurt, maybe the mango flavor. Get two of those."` | `["2 La Farmier mango yogurt"]` |
| `"some chicken, like chicken breast"` | `["chicken breast"]` |
| `"onions, maybe like a red onion"` | `["red onion"]` |
| `"mushrooms, the bella mushroom, portobello, whatever"` | `["portobello mushroom"]` |
| `"tomato paste 8oz, milk 2%, bread"` | `["tomato paste 8 oz", "milk 2%", "bread"]` |
| `"some shredded cheese, some eggs, some sour cream"` | `["shredded cheese", "eggs", "sour cream"]` |

### Input Template

```python
prompt = f"""{PARSER_SYSTEM_PROMPT}

Now parse this input:

{raw_text}

Return ONLY the JSON array, no other text."""
```

### Fallback Behavior

If the LLM response cannot be parsed as JSON, the input is split by newlines as a safe fallback:
```python
return [line.strip() for line in raw_text.split("\n") if line.strip()]
```

---

## Prompt 2 — Normalizer Agent

**File:** [`app/agents/normalizer.py`](https://github.com/basketsavings/slai/blob/main/app/agents/normalizer.py)  
**Called by:** `parse_and_normalize()` in `app/api/routes.py`  
**Temperature:** `0` (fully deterministic)

### Purpose

Takes each raw item string from the Parser and extracts structured fields: the canonical product name, quantity, unit, modifiers, notes, and whether a brand was specified by the user. The `has_brand` flag is critical — it drives the guardrail that decides whether to show brand-selection options in the UI.

### Full Prompt

```
You are a grocery item normalizer. Extract structured data from a single grocery item string.

CRITICAL RULES:
1. PRESERVE BRAND NAMES - Include brand in product name when user specifies one
2. PRESERVE FLAVOR/VARIETY - Include flavor/variety in product name
3. Move SIZE/WEIGHT to notes (8 oz, 2 lb, gallon) - these help but aren't core product
4. Extract quantity as NUMBER only (not units)
5. has_brand = true when ANY brand name is present
6. A **leading** number before the product is usually **item count** (e.g. **2 La Farmier mango yogurt**). **Size** on the product uses a unit (**8 oz**, **2 lb**)

BRAND HANDLING (IMPORTANT):
- has_brand = true ONLY if user explicitly named a brand (proper noun/company name)
- Brand names are proper nouns like: Häagen-Dazs, Kerrygold, La Farmier, Doritos, Chobani, Fairlife, etc.
- "Cool Ranch" is a FLAVOR of Doritos - Doritos is the brand
- Generic words are NOT brands: shredded, organic, fresh, dijon, bella, red, etc.
- When brand IS specified: normalized_product_name = "Brand Attribute Product"
- When NO brand: normalized_product_name = just the product with modifiers

Examples WITH brand:
  - "Häagen-Dazs vanilla bean ice cream" → has_brand: true, name: "Häagen-Dazs vanilla bean ice cream"
  - "Cool Ranch Doritos" → has_brand: true (Doritos is brand), name: "Cool Ranch Doritos"
  - "Kerrygold butter" → has_brand: true, name: "Kerrygold butter"
  - "La Farmier mango yogurt" → has_brand: true, name: "La Farmier mango yogurt"

Examples WITHOUT brand:
  - "eggs" → has_brand: false, name: "eggs"
  - "shredded cheese" → has_brand: false (shredded is modifier, not brand)
  - "red onion" → has_brand: false (red is variety, not brand)
  - "Dijon mustard" → has_brand: false (Dijon is a style, not a brand)
  - "portobello mushroom" → has_brand: false (portobello is variety)

ALTERNATIVES WITH "OR" (CRITICAL):
- If the user lists **two or more alternative specs** joined by **or** (e.g. "Ground beef 80/20 or 85/15", "milk 2% or whole"), set `normalized_product_name` to the **core product** only (e.g. "Ground beef", "milk") and set `notes` to **those specs as written** (e.g. "80/20 or 85/15", "2% or whole").
- If there is **only one** spec and **no** "or" (e.g. "Ground beef 80/20"), put the **full** product phrase in `normalized_product_name` (still split out quantity/unit if present) and leave `notes` empty unless something else needs a note.

SIZE/WEIGHT → NOTES:
- 8 oz, 16 oz, 1 lb, 2 lb, gallon, pint, etc. → move to notes (accept **8oz** or **8 oz**; when writing notes, prefer a space: **8 oz**)
- These are specifications, not core product identity

MODIFIERS (when no brand):
- organic, 2%, low fat, whole wheat, salted, unsalted, shredded, etc.

TYPO FIXES:
- "salt butter" → "salted butter", "unsalt" → "unsalted"
- "wht/wh" → "white", "org" → "organic"
- "pb" → "peanut butter", "oj" → "orange juice"

OUTPUT FORMAT:
{
  "normalized_product_name": "string - Brand + Attribute + Product if branded, OR just Product if generic",
  "quantity": number or null,
  "unit": null (move actual units like oz/lb to notes),
  "modifiers": ["array - only for generic products without brand"],
  "notes": "string - size specs (e.g. 8 oz), uncertainty, or alternatives",
  "has_brand": true if ANY brand mentioned, false otherwise
}
```

### Few-Shot Examples in Prompt

| Input | `normalized_product_name` | `has_brand` | `quantity` | `notes` | `modifiers` |
|-------|--------------------------|-------------|------------|---------|-------------|
| `"Häagen-Dazs vanilla bean ice cream"` | `"Häagen-Dazs vanilla bean ice cream"` | `true` | `null` | `""` | `[]` |
| `"Cool Ranch Doritos"` | `"Cool Ranch Doritos"` | `true` | `null` | `""` | `[]` |
| `"2 La Farmier yogurt mango flavor"` | `"La Farmier mango yogurt"` | `true` | `2` | `""` | `[]` |
| `"shredded cheese"` | `"cheese"` | `false` | `null` | `""` | `["shredded"]` |
| `"tomato paste 8 oz"` | `"tomato paste"` | `false` | `8` | `""` | `[]` |
| `"milk 2%"` | `"milk"` | `false` | `null` | `""` | `["2%"]` |
| `"Dijon mustard"` | `"Dijon mustard"` | `false` | `null` | `""` | `[]` |

### Input Templates

**Single item:**
```python
prompt = f"""{NORMALIZER_SYSTEM_PROMPT}

Now normalize this item:

"{raw_item}"

Return ONLY the JSON object, no other text."""
```

**Batch (all items in one call):**
```python
items_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(raw_items)])

prompt = f"""{NORMALIZER_SYSTEM_PROMPT}

Now normalize these items (return a JSON array with one object per item):

{items_text}

Return ONLY a JSON array like: [{"normalized_product_name": "...", ...}, ...]"""
```

> The batch call is always used in production — all items from the Parser are normalized in a single LLM request for speed.

### Fallback Behavior

If the JSON response fails to parse, each item falls back to using its raw string as the `normalized_product_name`:
```python
return NormalizedItem(
    normalized_product_name=raw_item.strip(),
    notes=f"Normalization failed: {str(e)}",
    original_text=raw_item
)
```

---

## Prompt 3 — Recipe Extraction (by Name)

**File:** [`app/agents/recipe.py`](https://github.com/basketsavings/slai/blob/main/app/agents/recipe.py)  
**Status:** Temporarily disabled at the route level (endpoint removed), agent code retained  
**Temperature:** `0.3` (slight creativity allowed for recipe generation)

### Purpose

Given a recipe name like `"Chicken Tikka Masala"`, generates a realistic and complete ingredient list with quantities, cuts, and varieties.

### Full Prompt

```
You are a recipe ingredient extractor. Given a recipe name, generate a realistic, complete ingredient list.

RULES:
1. Include ALL typical ingredients for the dish (don't skip basics like salt, oil, etc.)
2. Include realistic quantities and units
3. Use specific product names (e.g., "chicken breast" not just "chicken")
4. Include brand names ONLY for products that are typically branded (e.g., "Parmesan cheese")
5. Be specific about cuts, types, and varieties
6. Format each ingredient as: "quantity unit ingredient" (e.g., "2 lbs chicken breast")

OUTPUT FORMAT:
Return a JSON object:
{
  "recipe_name": "Full recipe name",
  "servings": number,
  "ingredients": [
    "1 lb ground beef",
    "2 tablespoons olive oil",
    ...
  ]
}
```

### Input Template

```python
prompt = f"""{RECIPE_EXTRACTION_PROMPT}

Now generate ingredients for this recipe:

Recipe: "{recipe_name}"

Return ONLY the JSON object, no other text."""
```

---

## Prompt 4 — Recipe Extraction (from URL)

**File:** [`app/agents/recipe.py`](https://github.com/basketsavings/slai/blob/main/app/agents/recipe.py)  
**Status:** Temporarily disabled at the route level  
**Temperature:** `0` (deterministic extraction)

### Purpose

Given HTML content scraped from a recipe webpage, extracts the ingredient list. Only used as a fallback if structured JSON-LD data is not present on the page.

### Full Prompt

```
You are a recipe ingredient extractor. Given HTML content from a recipe webpage, extract the ingredients list.

RULES:
1. Extract ALL ingredients mentioned in the recipe
2. Preserve exact quantities and units as written
3. Clean up any HTML artifacts or formatting issues
4. If ingredients have notes (like "divided" or "optional"), include them
5. Combine duplicate ingredients if they appear multiple times

OUTPUT FORMAT:
Return a JSON object:
{
  "recipe_name": "Recipe title from the page",
  "servings": number (if found, else null),
  "source_url": "original URL",
  "ingredients": [
    "ingredient 1 as written",
    "ingredient 2 as written",
    ...
  ]
}

Extract ingredients from this HTML content:
```

### Input Template

```python
prompt = f"""{URL_EXTRACTION_PROMPT}

URL: {url}

HTML Content:
{truncated_html}  # Capped at 15,000 characters (~4K tokens)

Return ONLY the JSON object, no other text."""
```

### Pre-LLM Optimization

Before calling the LLM for URL extraction, the agent attempts to extract structured data from JSON-LD `<script>` tags embedded in the page. If `recipeIngredient` is found in a `@type: Recipe` object, the LLM call is skipped entirely:

```python
def _extract_json_ld(self, html: str) -> dict | None:
    pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    # Parses JSON-LD and looks for @type: Recipe → recipeIngredient
```

---

## Guardrails & Confidence Scoring

**File:** [`app/services/resolver.py`](https://github.com/basketsavings/slai/blob/main/app/services/resolver.py)

This is fully deterministic code — no LLM involved. It evaluates the Autocomplete API results against the normalized item and assigns a confidence level.

### Scoring Rules

| Level | Criteria | SKU returned? | Numeric score |
|-------|----------|:-------------:|:-------------:|
| **HIGH** | Normalized name appears in API suggestion name, OR all significant search terms match | Only if `has_brand=true` and suggestion has real SKU | `0.95` |
| **MEDIUM** | At least one significant term (>2 chars) appears in API suggestion name | Never | `0.75` |
| **LOW** | No meaningful match, or no API results at all | Never | `0.45` |

### Matching Logic (HIGH confidence)

```python
# All top-3 API suggestions are checked
for s in top_suggestions:  # top 3
    sn = s.name.lower()
    if normalized_name in sn or all(term in sn for term in search_terms if len(term) > 2):
        high_matches.append(s)
```

### Matching Logic (MEDIUM confidence)

```python
# Top-5 API suggestions, any significant term matches
significant_terms = [t for t in search_terms if len(t) > 2]
for s in suggestions[:5]:
    sn = s.name.lower()
    if any(term in sn for term in significant_terms):
        medium_matches.append(s)
```

### SKU Guardrail

SKU is **only** included in the output when **all three** conditions are met:
1. Confidence is `HIGH`
2. The user specified a brand (`has_brand=true`)
3. The suggestion has a real numeric/string SKU (not a synthetic composite like `type_854_0`)

```python
use_sku = (
    suggestion.sku
    if user_specified_brand
    else (
        suggestion.sku
        if suggestion.suggestion_type == SuggestionType.PRODUCT
        and not suggestion.sku.startswith(("brand_", "type_", "item_"))
        else None
    )
)
```

```python
# Final output — SKU only at HIGH confidence
sku=resolved.sku if resolved.confidence == ConfidenceLevel.HIGH else None
```

---

## Brand Logic Guardrail

**File:** [`app/services/resolver.py`](https://github.com/basketsavings/slai/blob/main/app/services/resolver.py)

The `has_brand` flag from the Normalizer drives a key behavioral split:

| `has_brand` | `needs_specification` | Image shown? | Options shown? |
|:-----------:|:---------------------:|:------------:|:--------------:|
| `true` | `false` | Only if API brand matches user's brand | No |
| `false` | `true` | Yes (first API suggestion) | Yes (all relevant API options) |

### Brand Image Safety Check

When the user specified a brand, the image is only shown if the API suggestion's brand actually matches — preventing a wrong brand's image from appearing:

```python
def _brand_matches(self, normalized_item: NormalizedItem, suggestion: AutocompleteProduct) -> bool:
    user_text = normalized_item.normalized_product_name.lower()
    brand_lower = suggestion.brand.lower()
    
    # Direct substring match
    if brand_lower in user_text or user_text in brand_lower:
        return True
    
    # Strip legal suffixes: "The Happy Egg Co." → "happy egg"
    stop = ("the ", " co.", " inc.", " llc.", " ltd.", " corp.")
    brand_core = brand_lower
    for s in stop:
        brand_core = brand_core.replace(s, " ")
    
    # First significant word match
    words = [w for w in brand_lower.split() if w not in ("the", "a", "an") and len(w) > 1]
    return words[0] in user_text or (len(words) >= 2 and (words[0] + " " + words[1]) in user_text)
```

### Options Building

When `has_brand=false`, all API suggestions are surfaced as options for the user to choose from. Options are deduplicated by SKU:

```python
# First pass: brand variations of the SAME product
for suggestion in resolved.api_suggestions:
    if suggestion.brand is None:
        continue
    if base_product_name not in suggestion.name.lower():
        continue
    add_option(suggestion)

# Second pass: all remaining suggestions
for suggestion in resolved.api_suggestions:
    add_option(suggestion)
```

Certain compound words are excluded from the "same product" check to prevent false positives (e.g., "peanut butter" should not match as a brand variation of "butter"):
```python
words_before = suggestion_name_lower.split(base_product_name)[0].strip()
if words_before in ["peanut", "almond", "cashew", "sunflower", "apple", "coconut", "soy"]:
    continue
```

---

## Safe Fallback Behavior

Every layer has a fallback so the pipeline never crashes or returns empty results:

| Layer | Failure mode | Fallback |
|-------|-------------|---------|
| Parser (LLM) | JSON decode error | Split raw input by newlines |
| Normalizer (LLM) | JSON decode error | Use raw item string as `normalized_product_name` |
| Normalizer batch | Batch fails entirely | Re-run each item individually |
| Autocomplete API | HTTP error or timeout | Return empty suggestions list |
| Resolver (no suggestions) | Empty API result | Return `LOW` confidence item, `needs_specification=true` |
| Whole `/parse-list` endpoint | Unhandled exception | Split input by commas, return plain text items with `notes: "Processing failed"` |

---

## Output Contract Enforcement

**File:** [`app/models/schemas.py`](https://github.com/basketsavings/slai/blob/main/app/models/schemas.py)

The final `StructuredItem` is a Pydantic model that enforces the output contract at the type level. Key invariants that the code additionally enforces:

| Field | Invariant |
|-------|-----------|
| `sku` | `null` unless `confidence == HIGH`. Never invented by LLM. |
| `product_name` | Taken from the API suggestion name when matched; AI-normalized name only as last resort. |
| `image_url` | Sourced from Autocomplete API response only. Never fetched from a third-party at parse time. |
| `needs_specification` | `true` when user did not specify a brand (`has_brand=false`) and API returned results. |
| `options` | Only populated with real API suggestions; never generated by LLM. |
| `notes` | Contains original text for `LOW` confidence matches so nothing is silently lost. |
| `confidence` | Numeric score: `0.95` (HIGH), `0.75` (MEDIUM), `0.45` (LOW). |
| `match_source` | `"product"` (real SKU match), `"keyword"` (category match), or `"ai_text"` (no API match). |

```python
class StructuredItem(BaseModel):
    product_name: str
    sku: str | None = None               # null unless HIGH confidence + real SKU
    quantity: float | None = None
    unit: str | None = None
    category: str | None = None          # from API only
    image_url: str | None = None         # from API only
    brand: str | None = None
    size: str | None = None
    notes: str = ""
    needs_specification: bool = False
    options: list[ProductOption] = []    # from API only
    match_source: MatchSource = MatchSource.AI_TEXT
    match_reason: str = ""
    confidence: float = 0.0
    selected_option_index: int | None = None
    selected_suggestion_index: int | None = None
    total_suggestions: int | None = None
    autocomplete_query: str = ""         # phrase sent to Autocomplete (for debugging)
```

---

## GitHub Source Links

| Component | File |
|-----------|------|
| Parser prompt | [`app/agents/parser.py`](https://github.com/basketsavings/slai/blob/main/app/agents/parser.py) |
| Normalizer prompt | [`app/agents/normalizer.py`](https://github.com/basketsavings/slai/blob/main/app/agents/normalizer.py) |
| Recipe prompts | [`app/agents/recipe.py`](https://github.com/basketsavings/slai/blob/main/app/agents/recipe.py) |
| Confidence scoring & guardrails | [`app/services/resolver.py`](https://github.com/basketsavings/slai/blob/main/app/services/resolver.py) |
| Autocomplete API client | [`app/services/autocomplete.py`](https://github.com/basketsavings/slai/blob/main/app/services/autocomplete.py) |
| Output schema / contract | [`app/models/schemas.py`](https://github.com/basketsavings/slai/blob/main/app/models/schemas.py) |
| API pipeline orchestration | [`app/api/routes.py`](https://github.com/basketsavings/slai/blob/main/app/api/routes.py) |
