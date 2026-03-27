import time
from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import (
    AgentParseRequest, AgentParseResponse,
    AgentNormalizeRequest, AgentNormalizeResponse,
    AgentResolveRequest, AgentResolveResponse
)
from app.agents.parser import get_parser_agent
from app.agents.normalizer import get_normalizer_agent
from app.services.resolver import get_resolver
from app.services.tracking import capture_event
from app.api.routes import _client_ip

router = APIRouter()


@router.post("/parse", response_model=AgentParseResponse)
async def agent_parse(http_request: Request, request: AgentParseRequest) -> AgentParseResponse:
    """
    Step 1: Parse raw conversational input into individual grocery items.
    Uses the ParserAgent (Gemini) to extract strings.
    """
    start = time.perf_counter()
    raw_input = request.text or ""

    if not raw_input.strip():
        return AgentParseResponse(items=[])

    try:
        parser = get_parser_agent()
        parsed_items = parser.parse(raw_input)
        
        response = AgentParseResponse(items=parsed_items)
        try:
            await capture_event(
                client_ip=_client_ip(http_request),
                user_agent=http_request.headers.get("user-agent"),
                endpoint="/agents/parse",
                raw_input=raw_input,
                output_json=[{"item": i} for i in response.items],
                status="success",
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception:
            pass
            
        return response

    except Exception as e:
        print(f"Error in agent_parse: {e}")
        try:
            await capture_event(
                client_ip=_client_ip(http_request),
                user_agent=http_request.headers.get("user-agent"),
                endpoint="/agents/parse",
                raw_input=raw_input,
                output_json=[],
                status="error",
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to parse items: {str(e)}")


@router.post("/normalize", response_model=AgentNormalizeResponse)
async def agent_normalize(http_request: Request, request: AgentNormalizeRequest) -> AgentNormalizeResponse:
    """
    Step 2: Normalize individual item strings into structured data elements.
    Uses the NormalizerAgent (Gemini) to extract quantities, modifiers, brands, and notes.
    """
    start = time.perf_counter()
    raw_input_json = [i for i in request.items] if request.items else []
    
    if not request.items:
        return AgentNormalizeResponse(items=[])

    try:
        normalizer = get_normalizer_agent()
        normalized_items = normalizer.normalize_batch(request.items)
        
        response = AgentNormalizeResponse(items=normalized_items)
        try:
            await capture_event(
                client_ip=_client_ip(http_request),
                user_agent=http_request.headers.get("user-agent"),
                endpoint="/agents/normalize",
                raw_input=str(raw_input_json),
                output_json=[i.model_dump() for i in response.items],
                status="success",
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception:
            pass
            
        return response

    except Exception as e:
        print(f"Error in agent_normalize: {e}")
        try:
            await capture_event(
                client_ip=_client_ip(http_request),
                user_agent=http_request.headers.get("user-agent"),
                endpoint="/agents/normalize",
                raw_input=str(raw_input_json),
                output_json=[],
                status="error",
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to normalize items: {str(e)}")


@router.post("/resolve", response_model=AgentResolveResponse)
async def agent_resolve(http_request: Request, request: AgentResolveRequest) -> AgentResolveResponse:
    """
    Step 3: Resolve normalized items against the product catalog.
    Uses Autocomplete API to score confidence and assign SKUs.
    """
    start = time.perf_counter()
    raw_input_json = [i.model_dump() for i in request.items] if request.items else []
    
    if not request.items:
        return AgentResolveResponse(items=[])

    try:
        items = list(request.items)
        if request.prompt_context and request.prompt_context.strip():
            ctx = request.prompt_context.strip()
            items = [
                i.model_copy(update={"prompt_context": i.prompt_context or ctx}) for i in items
            ]
        resolver = get_resolver()
        structured_items = await resolver.resolve_batch(items)
        
        response = AgentResolveResponse(items=structured_items)
        try:
            await capture_event(
                client_ip=_client_ip(http_request),
                user_agent=http_request.headers.get("user-agent"),
                endpoint="/agents/resolve",
                raw_input=str(raw_input_json),
                output_json=[i.model_dump() for i in response.items],
                status="success",
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception:
            pass
            
        return response

    except Exception as e:
        print(f"Error in agent_resolve: {e}")
        try:
            await capture_event(
                client_ip=_client_ip(http_request),
                user_agent=http_request.headers.get("user-agent"),
                endpoint="/agents/resolve",
                raw_input=str(raw_input_json),
                output_json=[],
                status="error",
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception:
            pass
            
        raise HTTPException(status_code=500, detail=f"Failed to resolve items: {str(e)}")
