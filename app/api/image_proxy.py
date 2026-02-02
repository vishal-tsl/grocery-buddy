from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import httpx
from app.config import get_settings

router = APIRouter()


@router.get("/image-proxy")
async def proxy_image(url: str):
    """
    Proxy images from basketsavings with proper authentication headers.
    
    This endpoint fetches images from the basketsavings CDN using
    the same authentication as the Autocomplete API.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter required")
    
    # Only allow basketsavings images
    if not url.startswith("https://images.basketsavings.com/"):
        raise HTTPException(status_code=400, detail="Only basketsavings images allowed")
    
    settings = get_settings()
    
    # Try multiple header combinations
    headers = {
        "Authorization": settings.autocomplete_auth_token,
        "appName": settings.app_name,
        "appVersion": settings.app_version,
        "latitude": str(settings.autocomplete_lat),
        "longitude": str(settings.autocomplete_lng),
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.basketsavings.com/",
        "Origin": "https://www.basketsavings.com",
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Upstream returned {response.status_code}"
                )
            
            # Get content type from response
            content_type = response.headers.get("content-type", "image/jpeg")
            
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                }
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image fetch timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
