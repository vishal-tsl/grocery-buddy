import json
from google import genai
from app.config import get_settings
from app.models.schemas import NormalizedItem


NORMALIZER_SYSTEM_PROMPT = """You are a grocery item normalizer. Your job is to extract structured data from a single grocery item string.

RULES:
1. Extract the core product name (normalized, without quantity/unit)
2. FIX TYPOS and AUTOCOMPLETE partial names to proper grocery terms:
   - "salt butter" → "salted butter"
   - "unsalt butter" → "unsalted butter"  
   - "wht bread" → "white bread"
   - "org milk" → "organic milk"
   - "choc chip" → "chocolate chip cookies"
   - "pb" → "peanut butter"
   - "oj" → "orange juice"
3. Extract quantity if explicitly stated (number only)
4. Extract unit if explicitly stated (oz, lb, gallon, etc.)
5. Extract modifiers (organic, 2%, low fat, whole wheat, salted, unsalted, etc.)
6. Set has_brand to true ONLY if a specific brand name is mentioned (e.g., "Fairlife", "Kerrygold", "Horizon")
7. Move ANY uncertainty or unclear text to notes
8. NEVER guess brands or sizes - if not explicit, leave null
9. NEVER invent information that isn't in the input

COMMON AUTOCOMPLETE MAPPINGS:
- "salt/salted" as modifier for butter, nuts, crackers
- "unsalt/unsalted" as modifier for butter, nuts
- "wh/wht/white" → "white"
- "ww/wheat" → "whole wheat"
- "org" → "organic"
- "ff" → "fat free"
- "lf" → "low fat"
- "rf" → "reduced fat"

UNCERTAINTY INDICATORS (move to notes):
- "idk", "maybe", "or", "some", "I think", "?"
- Vague descriptions without specific products
- Multiple options mentioned

OUTPUT FORMAT:
Return a JSON object with these fields:
{
  "normalized_product_name": "string - the core product name (autocompleted/fixed)",
  "quantity": number or null,
  "unit": "string" or null,
  "modifiers": ["array", "of", "modifiers"],
  "notes": "string - any uncertainty or original unclear text",
  "has_brand": boolean - true only if a specific brand was mentioned
}

EXAMPLES:

Input: "salt butter"
Output: {"normalized_product_name": "butter", "quantity": null, "unit": null, "modifiers": ["salted"], "notes": "", "has_brand": false}

Input: "kerrygold butter"
Output: {"normalized_product_name": "butter", "quantity": null, "unit": null, "modifiers": [], "notes": "", "has_brand": true}

Input: "unsalt almonds"
Output: {"normalized_product_name": "almonds", "quantity": null, "unit": null, "modifiers": ["unsalted"], "notes": "", "has_brand": false}

Input: "tomato paste 8oz"
Output: {"normalized_product_name": "tomato paste", "quantity": 8, "unit": "oz", "modifiers": [], "notes": "", "has_brand": false}

Input: "milk 2%"
Output: {"normalized_product_name": "milk", "quantity": null, "unit": null, "modifiers": ["2%"], "notes": "", "has_brand": false}

Input: "fairlife milk 2%"
Output: {"normalized_product_name": "milk", "quantity": null, "unit": null, "modifiers": ["2%"], "notes": "", "has_brand": true}

Input: "organic whole wheat bread"
Output: {"normalized_product_name": "bread", "quantity": null, "unit": null, "modifiers": ["organic", "whole wheat"], "notes": "", "has_brand": false}

Input: "idk some chips"
Output: {"normalized_product_name": "chips", "quantity": null, "unit": null, "modifiers": [], "notes": "User unclear: 'idk some'", "has_brand": false}

Input: "wht bread"
Output: {"normalized_product_name": "bread", "quantity": null, "unit": null, "modifiers": ["white"], "notes": "", "has_brand": false}

Input: "org eggs"
Output: {"normalized_product_name": "eggs", "quantity": null, "unit": null, "modifiers": ["organic"], "notes": "", "has_brand": false}
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
                contents=prompt
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
                contents=prompt
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
