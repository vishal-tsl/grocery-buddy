import time
from fastapi import APIRouter, Request
from app.models.schemas import (
    ParseListRequest, ParseListResponse, StructuredItem, NormalizedItem,
    RecipeRequest, RecipeResponse
)
from app.services.resolver import get_resolver
from app.services.tracking import capture_event
from app.agents.parser import get_parser_agent
from app.agents.normalizer import get_normalizer_agent
from app.agents.recipe import get_recipe_agent


router = APIRouter()


def parse_and_normalize(text: str) -> list[NormalizedItem]:
    """Parse and normalize using the proper parser and normalizer agents."""
    parser = get_parser_agent()
    normalizer = get_normalizer_agent()
    
    # Step 1: Parse raw text into individual items
    raw_items = parser.parse(text)
    
    if not raw_items:
        return []
    
    # Step 2: Normalize each item using batch processing
    normalized_items = normalizer.normalize_batch(raw_items)
    
    return normalized_items


def _client_ip(req: Request) -> str:
    forwarded = req.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if req.client:
        return req.client.host or ""
    return ""


@router.post("/parse-list", response_model=ParseListResponse)
async def parse_list(http_request: Request, request: ParseListRequest) -> ParseListResponse:
    """
    Parse raw grocery text or RECIPE into a structured shopping list.
    
    Pipeline:
    1. Detect if input is a recipe name or URL
    2. If recipe/URL, use RecipeAgent to extract ingredients
    3. Normalize all items (batch)
    4. Resolve products (batch)
    """
    start = time.perf_counter()
    raw_input = request.text or ""

    if not raw_input.strip():
        return ParseListResponse(items=[])

    try:
        recipe_agent = get_recipe_agent()
        
        # Step 1: Decide if we should treat this as a recipe
        is_recipe_url = recipe_agent.is_url(raw_input)
        
        # Heuristic: URL or a multi-word phrase that doesn't look like a single item with brand
        # If it's 1 line and has common recipe words or is > 3 words and not a list
        is_recipe_request = is_recipe_url
        if not is_recipe_url and len(raw_input.splitlines()) == 1:
            words = raw_input.lower().split()
            recipe_keywords = ["recipe", "how to", "make", "easy", "best", "homemade", "dish", "meal"]
            if any(k in words for k in recipe_keywords) or (len(words) >= 4 and not any(c in raw_input for c in [",", "-", "[", "("])):
                is_recipe_request = True

        items_to_process = []
        
        if is_recipe_request:
            if is_recipe_url:
                recipe_data = await recipe_agent.extract_from_url(raw_input)
            else:
                recipe_data = recipe_agent.extract_from_name(raw_input)
            items_to_process = recipe_data.get("ingredients", [])
            print(f"DEBUG: Recipe detected, extracted {len(items_to_process)} ingredients")
        else:
            # Standard list parsing
            parser = get_parser_agent()
            items_to_process = parser.parse(raw_input)
            print(f"DEBUG: Standard list detected, parsed {len(items_to_process)} items")

        if not items_to_process:
            return ParseListResponse(items=[])

        # Step 2: Normalize
        normalizer = get_normalizer_agent()
        normalized_items = normalizer.normalize_batch(items_to_process)

        # Step 3: Resolve
        resolver = get_resolver()
        structured_items = await resolver.resolve_batch(normalized_items)
        
        total_time = time.perf_counter() - start
        
        response = ParseListResponse(items=structured_items)
        try:
            await capture_event(
                client_ip=_client_ip(http_request),
                user_agent=http_request.headers.get("user-agent"),
                endpoint="/parse-list",
                raw_input=raw_input,
                output_json=[i.model_dump() for i in structured_items],
                status="success",
                latency_ms=total_time * 1000,
            )
        except Exception:
            pass
        return response

    except Exception as e:
        print(f"Error in parse_list: {e}")
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
        response = ParseListResponse(items=fallback_items)
        try:
            await capture_event(
                client_ip=_client_ip(http_request),
                user_agent=http_request.headers.get("user-agent"),
                endpoint="/parse-list",
                raw_input=raw_input,
                output_json=[i.model_dump() for i in fallback_items],
                status="error",
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception:
            pass
        return response


