import json
from google import genai
from app.config import get_settings


PARSER_SYSTEM_PROMPT = """You are a grocery list parser that extracts individual products from CONVERSATIONAL input.

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
- Brand + Product + Flavor as ONE item (Häagen-Dazs vanilla bean ice cream)
- **ALT HANDLING (CRITICAL)**: If user says "X or Y" (e.g., "Ground beef 80/20 or 85/15"), extract it as ONE item "X" and move "or Y" to the notes.
- **CLEAN NAME**: Remove "(if available)" or "(optional)" from the product name and move to notes.
- **PRESERVE brands exactly** (Kerrygold, La Fermière, Haagen-Dazs). Strict spelling!
- PRESERVE flavor/variety (Cool Ranch, mango, vanilla bean).
- Attach quantity to the item ("get two of those" → add "2" to item).
- PRESERVE size/weight (8oz, 2lb).

DEDUPLICATION:
- If user says generic then specific, ONLY output the specific
- No duplicates - each unique product once

OUTPUT FORMAT:
Return a JSON array of strings, one unique product per item.

EXAMPLES:

Input: "Häagen-Dazs vanilla bean ice cream, Cool Ranch Doritos, Kerrygold butter, some eggs."

Output: ["Häagen-Dazs vanilla bean ice cream", "Cool Ranch Doritos", "Kerrygold butter", "eggs"]

Input: "yogurt, and for that, get the La Farmier yogurt, maybe the mango flavor. Get two of those."

Output: ["La Farmier mango yogurt 2"]

Input: "some chicken, like chicken breast"

Output: ["chicken breast"]

Input: "onions, maybe like a red onion"

Output: ["red onion"]

Input: "mushrooms, the bella mushroom, portobello, whatever"

Output: ["portobello mushroom"]

Input: "tomato paste 8oz, milk 2%, bread"

Output: ["tomato paste 8oz", "milk 2%", "bread"]

Input: "some shredded cheese, some eggs, some sour cream"

Output: ["shredded cheese", "eggs", "sour cream"]
"""


class ParserAgent:
    """Gemini-powered agent that splits raw grocery text into individual items."""
    
    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_id = "gemini-2.0-flash"
    
    def parse(self, raw_text: str) -> list[str]:
        """
        Parse raw grocery text into individual items.
        
        Args:
            raw_text: Multi-line, messy grocery input
            
        Returns:
            List of raw item strings, preserving original wording
        """
        if not raw_text or not raw_text.strip():
            return []
        
        prompt = f"""{PARSER_SYSTEM_PROMPT}

Now parse this input:

{raw_text}

Return ONLY the JSON array, no other text."""

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
                # Remove first and last lines (```json and ```)
                response_text = "\n".join(lines[1:-1])
            
            items = json.loads(response_text)
            
            # Validate output
            if not isinstance(items, list):
                return [raw_text.strip()]
            
            # Filter out empty strings and ensure all items are strings
            return [str(item).strip() for item in items if item and str(item).strip()]
            
        except (json.JSONDecodeError, Exception) as e:
            # Safe fallback: split by newlines
            return [line.strip() for line in raw_text.split("\n") if line.strip()]


# Singleton instance
_parser_agent: ParserAgent | None = None


def get_parser_agent() -> ParserAgent:
    """Get or create parser agent singleton."""
    global _parser_agent
    if _parser_agent is None:
        _parser_agent = ParserAgent()
    return _parser_agent
