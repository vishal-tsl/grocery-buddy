from fastapi import APIRouter, HTTPException
from app.models.schemas import ParseListRequest, ParseListResponse, StructuredItem, NormalizedItem
from app.services.resolver import get_resolver
from app.config import get_settings
from google import genai
import json


router = APIRouter()


# Minimal prompt for fast LLM processing
COMBINED_PROMPT = """Parse grocery items. Fix typos. Return JSON array.

Format: [{"n":"product","q":null,"u":null,"m":[],"b":false}]
- n: product name (lowercase, fix typos: "salt butter"→"salted butter")
- q: quantity (number or null)
- u: unit (oz/lb/gallon or null)
- m: modifiers ["organic","2%","salted"]
- b: true if brand mentioned (Kerrygold, Fairlife)

Example: "butter, milk 2%" → [{"n":"butter","q":null,"u":null,"m":[],"b":false},{"n":"milk","q":null,"u":null,"m":["2%"],"b":false}]"""


def parse_and_normalize(text: str) -> list[NormalizedItem]:
    """Parse and normalize using LLM to fix typos and correct product names."""
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)
    
    prompt = f"""{COMBINED_PROMPT}

Now process this input:

"{text}"

Return ONLY the JSON array, no other text."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        response_text = response.text.strip()
        
        # Clean up response
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        
        data_list = json.loads(response_text)
        
        results = []
        for data in data_list:
            # Support both short keys (n,q,u,m,b) and full keys
            name = data.get("n") or data.get("normalized_product_name", "")
            results.append(NormalizedItem(
                normalized_product_name=name,
                quantity=data.get("q") or data.get("quantity"),
                unit=data.get("u") or data.get("unit"),
                modifiers=data.get("m") or data.get("modifiers", []),
                notes="",
                original_text=name,
                has_brand=data.get("b") if "b" in data else data.get("has_brand", False)
            ))
        return results
        
    except Exception as e:
        print(f"LLM parsing failed: {e}")
        # Fallback: simple split without LLM correction
        items = [s.strip() for s in text.replace("\n", ",").split(",") if s.strip()]
        return [NormalizedItem(
            normalized_product_name=item,
            original_text=item
        ) for item in items]


@router.post("/parse-list", response_model=ParseListResponse)
async def parse_list(request: ParseListRequest) -> ParseListResponse:
    """
    Parse raw grocery text into a structured shopping list.
    
    Optimized pipeline:
    1. Single LLM call to parse AND normalize all items
    2. Parallel Autocomplete API calls for product resolution
    
    Returns a list of structured items conforming to the output contract.
    """
    import time
    start = time.time()
    
    if not request.text or not request.text.strip():
        return ParseListResponse(items=[])
    
    try:
        # Step 1: Parse and normalize with LLM (fixes typos)
        t1 = time.time()
        normalized_items = parse_and_normalize(request.text)
        llm_time = time.time()-t1
        
        if not normalized_items:
            return ParseListResponse(items=[])
        
        # Step 2: Resolve products (parallel API calls)
        t2 = time.time()
        resolver = get_resolver()
        structured_items = await resolver.resolve_batch(normalized_items)
        api_time = time.time()-t2
        total_time = time.time()-start
        
        # Log timing to response headers (visible to client)
        import logging
        logging.warning(f"TIMING: LLM={llm_time:.1f}s, API={api_time:.1f}s, Total={total_time:.1f}s for {len(normalized_items)} items")
        return ParseListResponse(items=structured_items)
        
    except Exception as e:
        print(f"Error in parse_list: {e}")
        
        # Safe fallback
        fallback_items = []
        for item in request.text.replace("\n", ",").split(","):
            item = item.strip()
            if item:
                fallback_items.append(StructuredItem(
                    product_name=item,
                    sku=None,
                    quantity=None,
                    unit=None,
                    notes="Processing failed"
                ))
        
        return ParseListResponse(items=fallback_items)
