import json
from google import genai
from app.config import get_settings
from app.models.schemas import NormalizedItem


NORMALIZER_SYSTEM_PROMPT = """You are a grocery item normalizer. Extract structured data from a single grocery item string.

CRITICAL RULES:
1. PRESERVE BRAND NAMES - Include brand in product name when user specifies one
2. PRESERVE FLAVOR/VARIETY - Include flavor/variety in product name
3. Extract unit (oz, lb, gallon, tbsp, etc.) into the unit field
4. Extract quantity as NUMBER only
5. has_brand = true when ANY brand name is present

BRAND HANDLING (IMPORTANT):
- has_brand = true ONLY if user explicitly named a brand (proper noun/company name)
- Brand names are proper nouns like: Häagen-Dazs, Kerrygold, La Fermière, Doritos, Chobani, Fairlife, etc.
- **STRICT SPELLING**: Always preserve brand spellings exactly as provided (e.g., "La Fermière").
- "Cool Ranch" is a FLAVOR of Doritos - Doritos is the brand
- Generic words are NOT brands: shredded, organic, fresh, dijon, bella, red, etc.
- When brand IS specified: normalized_product_name = "Brand Product Flavor/Variety"
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

SIZE/WEIGHT → NOTES:
- 8oz, 16oz, 1lb, 2lb, gallon, pint, etc. → move to notes
- These are specifications, not core product identity

MODIFIERS (when no brand):
- organic, 2%, low fat, whole wheat, salted, unsalted, shredded, etc.

TYPO FIXES:
- "salt butter" → "salted butter", "unsalt" → "unsalted"
- "wht/wh" → "white", "org" → "organic"
- "pb" → "peanut butter", "oj" → "orange juice"

OUTPUT FORMAT:
{
  "normalized_product_name": "string - Brand + Product + Flavor if branded, OR just Product if generic",
  "quantity": number or null,
  "unit": "string - the unit of measure (oz, lb, tbsp, cup, etc.)",
  "modifiers": ["array - only for generic products without brand"],
  "notes": "string - size specs (8oz), uncertainty, or alternatives",
  "has_brand": true if ANY brand mentioned, false otherwise
}

EXAMPLES:

Input: "Häagen-Dazs vanilla bean ice cream"
Output: {"normalized_product_name": "Häagen-Dazs vanilla bean ice cream", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": true}

Input: "Cool Ranch Doritos"
Output: {"normalized_product_name": "Cool Ranch Doritos", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": true}

Input: "Kerrygold butter"
Output: {"normalized_product_name": "Kerrygold butter", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": true}

Input: "La Farmier yogurt mango flavor 2"
Output: {"normalized_product_name": "La Farmier mango yogurt", "quantity": 2, "unit": null, "modifiers": [], "notes": "", "has_brand": true}

Input: "shredded cheese"
Output: {"normalized_product_name": "cheese", "quantity": null, "unit": null, "modifiers": ["shredded"], "notes": "", "has_brand": false}

Input: "tomato paste 8oz"
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
Output: {"normalized_product_name": "eggs", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": false}

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
Output: {"normalized_product_name": "Ground beef 80/20", "quantity": null, "unit": null, "modifiers": [], "notes": "or 85/15", "has_brand": false}
"""


class NormalizerAgent:
    """Gemini-powered agent that extracts structured data from grocery items."""
    
    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_id = "gemini-2.0-flash"
    
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
            
            return NormalizedItem(
                normalized_product_name=data.get("normalized_product_name", raw_item),
                quantity=data.get("quantity"),
                unit=data.get("unit"),
                modifiers=data.get("modifiers", []),
                notes=data.get("notes", ""),
                original_text=raw_item,
                has_brand=data.get("has_brand", False)
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
                results.append(NormalizedItem(
                    normalized_product_name=data.get("normalized_product_name", original),
                    quantity=data.get("quantity"),
                    unit=data.get("unit"),
                    modifiers=data.get("modifiers", []),
                    notes=data.get("notes", ""),
                    original_text=original,
                    has_brand=data.get("has_brand", False)
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
