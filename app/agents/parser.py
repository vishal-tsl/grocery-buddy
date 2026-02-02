import json
from google import genai
from app.config import get_settings


PARSER_SYSTEM_PROMPT = """You are a grocery list parser. Your ONLY job is to split raw grocery text input into individual line items.

RULES:
1. Split the input into separate grocery items
2. Preserve the original wording EXACTLY - do NOT correct spelling
3. Each item should be on its own line
4. Remove empty lines
5. Do NOT add any items that weren't in the original input
6. Do NOT merge items together
7. Do NOT interpret or normalize - just split

OUTPUT FORMAT:
Return a JSON array of strings, where each string is one grocery item exactly as written.

EXAMPLES:

Input: "tomato paste 8oz
milk 2%
bread"

Output: ["tomato paste 8oz", "milk 2%", "bread"]

Input: "eggs, butter, cheese"

Output: ["eggs", "butter", "cheese"]

Input: "idk some chips
maybe apples or oranges"

Output: ["idk some chips", "maybe apples or oranges"]
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
                contents=prompt
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
