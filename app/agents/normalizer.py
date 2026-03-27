import json
import re

from app.agents.gemini_util import require_genai_client
from app.models.schemas import ItemIntent, NormalizedItem

_SIZE_MODIFIERS = frozenset({"small", "medium", "large", "xl", "jumbo"})
_MEASURE_UNITS = frozenset({
    "oz", "lb", "lbs", "gal", "gallon", "gallons", "ml", "l", "kg", "g", "tbsp", "tsp",
    "cup", "cups", "pt", "pint", "pints", "qt", "quart", "quarts", "fl", "floz",
})
_COUNT_WORD_RE = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|dozen|half\s+dozen|couple|pair)\b",
    re.IGNORECASE,
)

# Long / pasted blocks: only a leading count counts. Mid-line "add 2 …" in a clause is not
# evidence for a different product on that same string.
_MAX_LONG_LINE_CHARS = 96
# Inline "3 tomatoes" / "12 eggs" only when the parsed line looks like one grocery phrase.
_MAX_INLINE_COUNT_LINE_CHARS = 48
_LEADING_ITEM_COUNT = re.compile(r"^\s*\d+")
_LEADING_COUNT_WORD = re.compile(
    r"^\s*(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|dozen|couple|pair)\b",
    re.IGNORECASE,
)
# "3 tomatoes", "12 eggs" — not "8 oz", "2%", "80/20"
_INLINE_ITEM_COUNT = re.compile(
    r"\b\d{1,3}\s+(?!oz\b|oz\.|lbs?\b|lb\.|g\b|kg\b|ml\b|ltr?\b|fl\.?\s*oz|%)(?=[a-zA-Z])",
    re.IGNORECASE,
)

# Grammatical plurals — NOT item counts. Models often output qty 2–6 from "breasts", "eggs", etc.
_PLURAL_GROCERY_WORDS = re.compile(
    r"\b("
    r"eggs|tomatoes|avocados|breasts|onions|potatoes|carrots|mushrooms|peppers|pickles|"
    r"olives|buns|rolls|fillets|cutlets|nachos|waffles|muffins|bagels|apples|oranges|"
    r"bananas|berries|grapes|beans|peas|sprouts|greens|crackers|cookies|chips|"
    r"noodles|wings|drumsticks|thighs|ribs|shrimp|scallops|clams|mussels|melons|lemons|"
    r"limes|mangoes|mangos|peaches|plums|cherries|sprinkles|croutons|croissants"
    r")\b",
    re.IGNORECASE,
)


def _line_has_item_count_evidence(text: str) -> bool:
    """True only if this line (not the whole monologue) states an item count."""
    t = (text or "").strip()
    if not t:
        return False
    low = t.lower()
    if len(t) > _MAX_LONG_LINE_CHARS:
        return bool(_LEADING_ITEM_COUNT.match(t)) or bool(_LEADING_COUNT_WORD.match(t))
    if _LEADING_ITEM_COUNT.match(t) or _LEADING_COUNT_WORD.match(t):
        return True
    if _COUNT_WORD_RE.search(low):
        return True
    if len(t) <= _MAX_INLINE_COUNT_LINE_CHARS and _INLINE_ITEM_COUNT.search(t):
        return True
    return False


def apply_normalizer_guardrails(item: NormalizedItem) -> NormalizedItem:
    """Idempotent cleanup: quantity + modifiers. Call after batch normalize (e.g. from API)."""
    return item.model_copy(
        update={
            "quantity": _sanitize_quantity(
                item.original_text,
                item.quantity,
                unit=item.unit,
                product_name=item.normalized_product_name,
            ),
            "modifiers": _modifiers_only_if_on_line(item.modifiers, item.original_text),
        }
    )


def _modifiers_only_if_on_line(modifiers: list[str], original: str) -> list[str]:
    """Drop produce-size modifiers the model copied from other batch lines."""
    ot = original.lower()
    out: list[str] = []
    for m in modifiers:
        if not isinstance(m, str):
            continue
        ml = m.lower().strip()
        if ml in _SIZE_MODIFIERS and ml not in ot:
            continue
        out.append(m)
    return out


def _quantity_from_plural_noun_only(
    q: float,
    original: str,
    product_name: str | None,
) -> bool:
    """
    True if q is a small integer likely invented from grammatical plural (s/es), not user count.
    Allows '3 tomatoes' when the digit 3 appears; blocks stray digits elsewhere in a long clause.
    """
    if q < 2 or q > 6:
        return False

    low_orig = (original or "").lower()
    blob = f"{low_orig} {(product_name or '').lower()}"
    if not _PLURAL_GROCERY_WORDS.search(blob):
        return False

    if _COUNT_WORD_RE.search(low_orig):
        return False

    qi = int(q)
    if re.search(rf"\b{qi}\b", original or ""):
        return False

    return True


def _sanitize_quantity(
    original: str,
    quantity: float | None,
    *,
    unit: str | None = None,
    product_name: str | None = None,
) -> float | None:
    """
    Strict guardrails: keep quantity only when this line explicitly supports a count.
    Drops model-invented counts (e.g. 'some eggs' → 12, 'some tomatoes' → 3).
    When `unit` is a measure (oz, lb, …), trust quantity as size/weight, not item count.
    """
    if quantity is None:
        return None
    try:
        q = float(quantity)
    except (TypeError, ValueError):
        return quantity

    low = original.lower()
    u = (unit or "").strip().lower().split()[0] if unit else ""
    if u in _MEASURE_UNITS:
        return q

    if not _line_has_item_count_evidence(original):
        return None

    if q == 2.0 and re.search(r"\btoo\b", low) and not re.search(r"\b(2|two)\b", low):
        return None

    if q == 12.0 and not (
        re.search(r"\b12\b", original) or re.search(r"\bdozen\b", low)
    ):
        return None

    if q >= 2.0 and not re.search(r"\d", original) and not _COUNT_WORD_RE.search(low):
        return None

    if _quantity_from_plural_noun_only(q, original, product_name):
        return None

    return q


NORMALIZER_SYSTEM_PROMPT = """You are a grocery item normalizer. Extract structured data from a single grocery item string.

CRITICAL RULES:
1. PRESERVE BRAND NAMES - Include brand in product name when user specifies one
1b. Never put the phrase **As written:** in `notes` (or any near-duplicate). User-facing notes are for sizes, alternatives, or uncertainty only.
2. PRESERVE FLAVOR/VARIETY - Include flavor/variety in product name
3. Extract unit (oz, lb, gallon, tbsp, etc.) into the unit field
4. Extract quantity as NUMBER only
5. has_brand = true when ANY brand name is present
6. A **leading** number before the product is usually **item count** (e.g. **2 La Fermière mango yogurt**). **Size** on the product uses a unit (**8 oz**, **2 lb**).

QUANTITY (CRITICAL — downstream enforces this strictly):
- **`quantity` must be `null` unless this exact line** contains a **numeral** (0–9) **or** a count word (**one, two, three, dozen, couple, pair,** …).
- **"some"**, **"a few"**, **"maybe"**, **"like"** without a number → **`quantity`: null** (do not guess 1, 2, 3, 8, or 12).
- **Never** use plural nouns ("eggs", "breasts", "tomatoes") or **-s / -es endings** as a quantity — grammar is not math. Only numerals and count words set `quantity`.
- For **12 eggs**, the line must say **12** or **dozen** — not "some eggs".
- The word **"too"** (*also*) is **not** the number **2**.

BATCH / NUMBERED LISTS (CRITICAL):
- Each numbered line is **isolated**. Words like **small**, **medium**, **large** go in `modifiers` **only** if that word appears **on that same line** (e.g. "1 medium cucumber"). **Never** copy size words from another line onto tomatoes, bell pepper, avocado, etc.

BRAND HANDLING (IMPORTANT):
- has_brand = true ONLY if user explicitly named a brand (proper noun/company name)
- Brand names are proper nouns like: Häagen-Dazs, Kerrygold, La Fermière, Doritos, Chobani, Fairlife, etc.
- **STRICT SPELLING**: Always preserve brand spellings exactly as provided (e.g., "La Fermière").
- "Cool Ranch" is a FLAVOR of Doritos - Doritos is the brand
- Generic words are NOT brands: shredded, organic, fresh, dijon, bella, red, etc.
- When brand IS specified: normalized_product_name = "Brand Attribute Product"
- When NO brand: normalized_product_name = just the product with modifiers

TERMINOLOGY MAPPING (for better API matches):
- **Fat Content**: Map "full-fat" (yogurt/milk) to "whole milk" or "5%".
- **Protein**: Map "protein-enriched" to "high protein".
- **Low Fat**: Map "low-fat" to "2%".
- These mappings help the downstream resolver find products the API understands.

Examples WITH brand:
  - "Häagen-Dazs vanilla bean ice cream" → has_brand: true, name: "Häagen-Dazs vanilla bean ice cream"
  - "Cool Ranch Doritos" → has_brand: true (Doritos is brand), name: "Cool Ranch Doritos"
  - "Kerrygold butter" → has_brand: true, name: "Kerrygold butter"
  - "La Fermière mango yogurt" → has_brand: true, name: "La Fermière mango yogurt"

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
- 8 oz, 16 oz, 1 lb, 2 lb, gallon, pint, etc. → move to notes (accept **8oz** or **8 oz** from users; when writing notes, prefer a space: **8 oz**)
- These are specifications, not core product identity

MODIFIERS (when no brand):
- organic, 2%, low fat, whole wheat, salted, unsalted, shredded, etc.

TYPO FIXES:
- "salt butter" → "salted butter", "unsalt" → "unsalted"
- "wht/wh" → "white", "org" → "organic"
- "pb" → "peanut butter", "oj" → "orange juice"

ITEM INTENT (classify the line):
- "generic" — staple with no brand (eggs, milk, taco shells as a phrase is still generic unless a brand appears)
- "branded" — user named a company/proper brand
- "ambiguous" — could be many products (e.g. single word "shells", "sauce")

OUTPUT FORMAT:
{
  "normalized_product_name": "string - Brand + Attribute + Product if branded, OR just Product if generic",
  "quantity": number or null,
  "unit": "string - the unit of measure (oz, lb, tbsp, cup, etc.)",
  "modifiers": ["array - only for generic products without brand"],
  "notes": "string - size specs (e.g. 8 oz), uncertainty, or alternatives",
  "has_brand": true if ANY brand mentioned, false otherwise,
  "item_intent": "generic" | "branded" | "ambiguous"
}

EXAMPLES:

Input: "Häagen-Dazs vanilla bean ice cream"
Output: {"normalized_product_name": "Häagen-Dazs vanilla bean ice cream", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": true, "item_intent": "branded"}

Input: "Cool Ranch Doritos"
Output: {"normalized_product_name": "Cool Ranch Doritos", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": true}

Input: "Kerrygold butter"
Output: {"normalized_product_name": "Kerrygold butter", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": true}

Input: "2 La Fermière yogurt mango flavor"
Output: {"normalized_product_name": "La Fermière mango yogurt", "quantity": 2, "unit": null, "modifiers": [], "notes": "", "has_brand": true, "item_intent": "branded"}

Input: "shredded cheese"
Output: {"normalized_product_name": "cheese", "quantity": null, "unit": null, "modifiers": ["shredded"], "notes": "", "has_brand": false}

Input: "tomato paste 8 oz"
Output: {"normalized_product_name": "tomato paste", "quantity": 8, "unit": "oz", "modifiers": [], "notes": "", "has_brand": false}

Input: "chicken breast"
Output: {"normalized_product_name": "chicken breast", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": false}

Input: "bella mushroom portobello"
Output: {"normalized_product_name": "portobello mushroom", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": false}

Input: "red onion"
Output: {"normalized_product_name": "red onion", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": false}

Input: "milk 2%"
Output: {"normalized_product_name": "milk", "quantity": null, "unit": null, "modifiers": ["2%"], "notes": "", "has_brand": false}

Input: "heavy cream"
Output: {"normalized_product_name": "heavy cream", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": false}

Input: "eggs"
Output: {"normalized_product_name": "eggs", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": false, "item_intent": "generic"}

Input: "paper towels"
Output: {"normalized_product_name": "paper towels", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": false}

Input: "Dijon mustard"
Output: {"normalized_product_name": "Dijon mustard", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": false}

Input: "2 lbs chicken breast"
Output: {"normalized_product_name": "chicken breast", "quantity": 2, "unit": "lbs", "modifiers": [], "notes": "", "has_brand": false}

Input: "sour cream"
Output: {"normalized_product_name": "sour cream", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": false}

Input: "Greek yogurt plain full-fat"
Output: {"normalized_product_name": "Greek yogurt", "quantity": null, "unit": null, "modifiers": ["plain", "5%"], "notes": "", "has_brand": false}

Input: "protein-enriched milk"
Output: {"normalized_product_name": "milk", "quantity": null, "unit": null, "modifiers": ["high protein"], "notes": "", "has_brand": false}

Input: "Ground beef 80/20 or 85/15"
Output: {"normalized_product_name": "Ground beef", "quantity": null, "unit": null, "modifiers": [], "notes": "80/20 or 85/15", "has_brand": false}

Input: "Ground beef 80/20"
Output: {"normalized_product_name": "Ground beef 80/20", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": false}
"""


def _parse_item_intent(data: dict) -> ItemIntent | None:
    raw = data.get("item_intent")
    if raw in ("generic", "branded", "ambiguous"):
        return ItemIntent(raw)
    return None


class NormalizerAgent:
    """Gemini-powered agent that extracts structured data from grocery items."""
    
    def __init__(self):
        self._client = None
        self.model_id = "gemini-2.0-flash"

    @property
    def client(self):
        if self._client is None:
            self._client = require_genai_client()
        return self._client
    
    def normalize(self, raw_item: str) -> NormalizedItem:
        """
        Normalize a single grocery item string into structured data.
        
        Args:
            raw_item: Single grocery item string
            
        Returns:
            NormalizedItem with extracted structure
        """
        if not raw_item or not raw_item.strip():
            return NormalizedItem(
                normalized_product_name="unknown",
                notes="Empty input",
                original_text=raw_item
            )
        
        prompt = f"""{NORMALIZER_SYSTEM_PROMPT}

Now normalize this item:

"{raw_item}"

Return ONLY the JSON object, no other text."""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={"temperature": 0}  # Deterministic output
            )
            response_text = response.text.strip()
            
            # Clean up response - remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            data = json.loads(response_text)
            mods = _modifiers_only_if_on_line(data.get("modifiers", []) or [], raw_item)
            qty = _sanitize_quantity(
                raw_item,
                data.get("quantity"),
                unit=data.get("unit"),
                product_name=data.get("normalized_product_name"),
            )

            return NormalizedItem(
                normalized_product_name=data.get("normalized_product_name", raw_item),
                quantity=qty,
                unit=data.get("unit"),
                modifiers=mods,
                notes=data.get("notes", ""),
                original_text=raw_item,
                has_brand=data.get("has_brand", False),
                item_intent=_parse_item_intent(data),
            )
            
        except (json.JSONDecodeError, Exception) as e:
            # Safe fallback: use raw item as product name
            return NormalizedItem(
                normalized_product_name=raw_item.strip(),
                notes=f"Normalization failed: {str(e)}",
                original_text=raw_item
            )
    
    def normalize_batch(self, raw_items: list[str]) -> list[NormalizedItem]:
        """
        Normalize multiple grocery items in a SINGLE LLM call for speed.
        
        Args:
            raw_items: List of raw grocery item strings
            
        Returns:
            List of NormalizedItem objects
        """
        if not raw_items:
            return []
        
        # Single LLM call for all items (much faster)
        items_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(raw_items)])
        
        prompt = f"""{NORMALIZER_SYSTEM_PROMPT}

Now normalize these items (return a JSON array with one object per item):

{items_text}

Return ONLY a JSON array like: [{{"normalized_product_name": "...", ...}}, ...]"""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={"temperature": 0}  # Deterministic output
            )
            response_text = response.text.strip()
            
            # Clean up response
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            data_list = json.loads(response_text)
            
            results = []
            for i, data in enumerate(data_list):
                original = raw_items[i] if i < len(raw_items) else ""
                mods = _modifiers_only_if_on_line(data.get("modifiers", []) or [], original)
                qty = _sanitize_quantity(
                    original,
                    data.get("quantity"),
                    unit=data.get("unit"),
                    product_name=data.get("normalized_product_name"),
                )
                results.append(NormalizedItem(
                    normalized_product_name=data.get("normalized_product_name", original),
                    quantity=qty,
                    unit=data.get("unit"),
                    modifiers=mods,
                    notes=data.get("notes", ""),
                    original_text=original,
                    has_brand=data.get("has_brand", False),
                    item_intent=_parse_item_intent(data),
                ))
            return results
            
        except Exception as e:
            # Fallback: process individually if batch fails
            print(f"Batch normalization failed: {e}, falling back to individual")
            return [self.normalize(item) for item in raw_items]


# Singleton instance
_normalizer_agent: NormalizerAgent | None = None


def get_normalizer_agent() -> NormalizerAgent:
    """Get or create normalizer agent singleton."""
    global _normalizer_agent
    if _normalizer_agent is None:
        _normalizer_agent = NormalizerAgent()
    return _normalizer_agent
