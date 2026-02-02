import httpx
from app.config import get_settings
from app.models.schemas import AutocompleteProduct


class AutocompleteClient:
    """Async client for the Autocomplete API - the ONLY source of truth for products."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.autocomplete_base_url
    
    def _get_headers(self) -> dict[str, str]:
        """Get required headers for API requests."""
        return {
            "Authorization": self.settings.autocomplete_auth_token,
            "appName": self.settings.app_name,
            "appVersion": self.settings.app_version,
            "latitude": str(self.settings.autocomplete_lat),
            "longitude": str(self.settings.autocomplete_lng),
        }
    
    async def search(self, query: str) -> list[AutocompleteProduct]:
        """
        Search for products using the Autocomplete API.
        
        Args:
            query: Normalized product name to search for
            
        Returns:
            List of AutocompleteProduct suggestions from the API
        """
        if not query or not query.strip():
            return []
        
        params = {
            "query": query.strip(),
            "limit": str(self.settings.autocomplete_limit),
            "includeProducts": "true",
            "includeImages": str(self.settings.autocomplete_include_images).lower(),
            "excludeSubcategory": str(self.settings.autocomplete_exclude_subcategory).lower(),
            "exludeBrand": str(self.settings.autocomplete_exclude_brand).lower(),  # Note: API has typo "exlude"
            "semanticEnabled": "true",
            "enrichKeyword": "true",
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.base_url,
                    headers=self._get_headers(),
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                return self._parse_response(data)
                
        except httpx.HTTPError as e:
            # Log error but return empty list - fail safely
            print(f"Autocomplete API error for '{query}': {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in autocomplete for '{query}': {e}")
            return []
    
    def _parse_response(self, data: dict) -> list[AutocompleteProduct]:
        """
        Parse API response into AutocompleteProduct objects.
        
        Expected response structure from basketsavings API:
        {
            "content": {
                "suggests": [
                    {
                        "id": 854,
                        "type": "Type",
                        "name": "Milk",
                        "category": "Dairy & Eggs",
                        "typeId": 854,
                        "typeName": "Milk",
                        "brandId": null,
                        "brandName": null,
                        "imageUrl": null,
                        "size": null
                    }
                ]
            }
        }
        """
        products = []
        
        # Extract suggests from the basketsavings API response
        product_list = []
        
        if isinstance(data, dict):
            # Primary: basketsavings API structure
            if "content" in data and isinstance(data["content"], dict):
                product_list = data["content"].get("suggests", [])
            # Fallback structures
            elif "suggests" in data:
                product_list = data["suggests"]
            elif "products" in data:
                product_list = data["products"]
            elif "results" in data:
                product_list = data["results"]
        elif isinstance(data, list):
            product_list = data
        
        for idx, item in enumerate(product_list):
            if not isinstance(item, dict):
                continue
            
            # Extract product info from basketsavings API format
            # For "Keyword" type, id is null, so use brandId + typeId or generate unique id
            sku = item.get("id") or item.get("sku") or item.get("productId")
            
            # For Keyword items without id, create a composite identifier
            if not sku:
                brand_id = item.get("brandId")
                type_id = item.get("typeId")
                if brand_id and type_id:
                    sku = f"brand_{brand_id}_type_{type_id}"
                elif type_id:
                    sku = f"type_{type_id}_{idx}"
                else:
                    sku = f"item_{idx}"
            
            name = item.get("name") or item.get("productName") or item.get("typeName") or ""
            
            if not name:
                continue
            
            # Extract category
            category = item.get("category") or item.get("categoryName")
            
            # Handle nested category objects
            if isinstance(category, dict):
                category = category.get("name") or category.get("categoryName")
            
            # Build full image URL if present
            image_url = item.get("imageUrl")
            if image_url and not image_url.startswith("http"):
                # Prefix with base URL for basketsavings images
                image_url = f"https://images.basketsavings.com/{image_url}"
            
            products.append(AutocompleteProduct(
                sku=str(sku),
                name=str(name),
                brand=item.get("brandName") or item.get("brand"),
                category=str(category) if category else None,
                type_id=item.get("typeId"),
                type_name=item.get("typeName"),
                image_url=image_url,
                size=item.get("size")
            ))
        
        return products


# Singleton instance
_autocomplete_client: AutocompleteClient | None = None


def get_autocomplete_client() -> AutocompleteClient:
    """Get or create autocomplete client singleton."""
    global _autocomplete_client
    if _autocomplete_client is None:
        _autocomplete_client = AutocompleteClient()
    return _autocomplete_client
