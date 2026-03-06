import time
from fastapi import APIRouter, Request
from app.models.schemas import (
    ParseListRequest, ParseListResponse, StructuredItem, NormalizedItem
)
from app.services.resolver import get_resolver
from app.services.tracking import capture_event
from app.agents.parser import get_parser_agent
from app.agents.normalizer import get_normalizer_agent


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
    Parse raw grocery text into a structured shopping list.
    
    Optimized pipeline:
    1. Single LLM call to parse AND normalize all items
    2. Parallel Autocomplete API calls for product resolution
    
    Returns a list of structured items conforming to the output contract.
    """
    start = time.perf_counter()
    raw_input = request.text or ""

    if not raw_input.strip():
        return ParseListResponse(items=[])

    try:
        t1 = time.perf_counter()
        normalized_items = parse_and_normalize(request.text)
        llm_time = time.perf_counter() - t1

        if not normalized_items:
            response = ParseListResponse(items=[])
            try:
                await capture_event(
                    client_ip=_client_ip(http_request),
                    user_agent=http_request.headers.get("user-agent"),
                    endpoint="/parse-list",
                    raw_input=raw_input,
                    output_json=[i.model_dump() for i in response.items],
                    status="success",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )
            except Exception:
                pass
            return response

        t2 = time.perf_counter()
        resolver = get_resolver()
        structured_items = await resolver.resolve_batch(normalized_items)
        api_time = time.perf_counter() - t2
        total_time = time.perf_counter() - start

        import logging
        logging.warning(
            "TIMING: LLM=%.1fs, API=%.1fs, Total=%.1fs for %s items",
            llm_time, api_time, total_time, len(normalized_items),
        )
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


# Recipe module temporarily disabled.
# To re-enable, restore RecipeRequest/RecipeResponse imports,
# the get_recipe_agent import, and the /recipe-to-list endpoint below.
