import json
import re

from app.agents.gemini_util import require_genai_client

# Markdown-style checklist prefixes are metadata only — never exclude the line.
_CHECKBOX_LINE = re.compile(r"^\s*\[[\sxX]\]\s*")


def _line_items_from_stripped(raw_text: str) -> list[str]:
    out: list[str] = []
    for line in raw_text.splitlines():
        s = _CHECKBOX_LINE.sub("", line).strip()
        if s:
            out.append(s)
    return out


def _dedupe_items_case_insensitive(items: list[str]) -> list[str]:
    """Drop exact duplicates differing only by case/spacing (LLM often repeats a brand line)."""
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        k = re.sub(r"\s+", " ", x.strip()).lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x.strip())
    return out


def merge_line_items_with_llm(llm_items: list[str], line_items: list[str]) -> list[str]:
    """Union LLM output with deterministic line items (order: LLM first, then missing lines)."""
    seen = {x.strip().lower() for x in llm_items if x and str(x).strip()}
    merged = [str(x).strip() for x in llm_items if x and str(x).strip()]
    for line in line_items:
        k = line.strip().lower()
        if k and k not in seen:
            seen.add(k)
            merged.append(line.strip())
    return merged


PARSER_SYSTEM_PROMPT = """You are a grocery list parser that extracts individual products from CONVERSATIONAL input.

YOUR JOB:
Extract ONLY unique grocery products. Remove ALL conversational noise and duplicates.

NOISE TO REMOVE (never include as items):
- Greetings/closings: "Okay", "Let's make", "Thanks", "That's it", "Oh actually"
- Fillers: "and", "then", "also", "um", "like", "maybe", "I think", "some"
- Instructions: "Let's get", "Get me", "I need", "for that get", "add"

CHECKBOX / TASK LISTS (CRITICAL):
- Lines like `[ ] butter`, `[x] eggs`, or `[X] milk` are **checklist markers only**.
- **Always include** the product text; `[x]` does NOT mean "done" or "exclude" — treat it like decoration.
- Strip the `[ ]` / `[x]` prefix mentally and output the item name only (e.g. `[x] eggs` → `eggs`).

CLARIFICATION HANDLING (CRITICAL):
When user clarifies or specifies a vague item, ONLY keep the FINAL specific version:
- "some chicken, like chicken breast" → "chicken breast" (NOT "chicken" AND "chicken breast")
- "onions, maybe like a red onion" → "red onion" (NOT "onions" AND "red onion")
- "mushrooms, the bella mushroom, portobello, whatever" → "portobello mushroom" (ONLY final one)
- "yogurt, and for that, get La Fermière yogurt mango flavor" → copy the brand spelling **exactly** from the user (ONLY the specific)
- "get some X, and for that, get Y" means Y replaces X - output ONLY Y

WHAT TO EXTRACT:
- Brand + Attribute + Product as ONE item (Häagen-Dazs vanilla bean ice cream)
- **ALT HANDLING (CRITICAL)**: If user gives **alternatives** with **or** (e.g. "Ground beef 80/20 or 85/15"), output **one** string with their **full** wording — do not drop alternatives. Downstream normalization will use base product **Ground beef** and notes **80/20 or 85/15**. If user gives **only one** spec and **no** "or" (e.g. "Ground beef 80/20"), output that **entire** phrase as one item so it stays the full product name.
- **CLEAN NAME**: Remove "(if available)" or "(optional)" from the product name and move to notes.
- **PRESERVE brands exactly** (Kerrygold, La Fermière, Haagen-Dazs). Strict spelling!
- PRESERVE flavor/variety (Cool Ranch, mango, vanilla bean).
- Attach item **count** at the **start** of the string ("get two of those" → **"2 …"** before the product name, not after).
- PRESERVE size/weight; in output strings use a **space** between number and unit (**8 oz**, **2 lb**). Users may type "8oz" — normalize spacing in your outputs.

DEDUPLICATION:
- If user says generic then specific, ONLY output the specific
- No duplicates - each unique product once (even in a long spoken-style paragraph, output each product **once**)
- The same brand + product must appear **once** only (e.g. one "Häagen-Dazs vanilla bean ice cream", not two strings that differ only by spelling or spacing)

OUTPUT FORMAT:
Return a JSON array of strings, one unique product per item.

EXAMPLES:

Input: "Häagen-Dazs vanilla bean ice cream, Cool Ranch Doritos, Kerrygold butter, some eggs."

Output: ["Häagen-Dazs vanilla bean ice cream", "Cool Ranch Doritos", "Kerrygold butter", "eggs"]

Input: "yogurt, and for that, get the La Fermière yogurt, maybe the mango flavor. Get two of those."

Output: ["2 La Fermière mango yogurt"]

Input: "some chicken, like chicken breast"

Output: ["chicken breast"]

Input: "onions, maybe like a red onion"

Output: ["red onion"]

Input: "mushrooms, the bella mushroom, portobello, whatever"

Output: ["portobello mushroom"]

Input: "tomato paste 8oz, milk 2%, bread"

Output: ["tomato paste 8 oz", "milk 2%", "bread"]

Input: "some shredded cheese, some eggs, some sour cream"

Output: ["shredded cheese", "eggs", "sour cream"]

Input: "[x] taco shells
[ ] ground beef
[x] cheese"

Output: ["taco shells", "ground beef", "cheese"]
"""


class ParserAgent:
    """Gemini-powered agent that splits raw grocery text into individual items."""
    
    def __init__(self):
        self._client = None
        self.model_id = "gemini-2.0-flash"

    @property
    def client(self):
        if self._client is None:
            self._client = require_genai_client()
        return self._client
    
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

        stripped = "\n".join(
            _CHECKBOX_LINE.sub("", line) for line in raw_text.splitlines()
        )
        raw_text = stripped if stripped.strip() else raw_text
        deterministic_lines = _line_items_from_stripped(raw_text)

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
            parsed = [str(item).strip() for item in items if item and str(item).strip()]
            merged = merge_line_items_with_llm(parsed, deterministic_lines)
            return _dedupe_items_case_insensitive(merged)
            
        except (json.JSONDecodeError, Exception) as e:
            # Safe fallback: split by newlines
            fb = [line.strip() for line in raw_text.split("\n") if line.strip()]
            merged = merge_line_items_with_llm(fb, deterministic_lines)
            return _dedupe_items_case_insensitive(merged)


# Singleton instance
_parser_agent: ParserAgent | None = None


def get_parser_agent() -> ParserAgent:
    """Get or create parser agent singleton."""
    global _parser_agent
    if _parser_agent is None:
        _parser_agent = ParserAgent()
    return _parser_agent
