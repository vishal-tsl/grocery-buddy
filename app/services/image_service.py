"""
OpenFoodFacts image service for fetching public product images.
"""
import httpx


class ImageService:
    """Service for fetching product images from OpenFoodFacts."""
    
    BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"
    
    def __init__(self):
        self._cache: dict[str, str | None] = {}
    
    async def get_product_image(self, product_name: str) -> str | None:
        """
        Search OpenFoodFacts for a product and return its image URL.
        Returns None if no image found (UI will show placeholder icon).
        
        Args:
            product_name: The product name to search for
            
        Returns:
            Image URL from OpenFoodFacts or None
        """
        # Check cache first
        cache_key = product_name.lower().strip()
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            params = {
                "search_terms": product_name,
                "search_simple": "1",
                "action": "process",
                "json": "1",
                "page_size": "1",  # Only need one result
                "fields": "product_name,image_small_url,image_url,brands"
            }
            
            async with httpx.AsyncClient(timeout=2.0) as client:  # Fast timeout for speed
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                
                products = data.get("products", [])
                if products and len(products) > 0:
                    product = products[0]
                    # Prefer small image (200px) for thumbnails, fall back to full image
                    image_url = product.get("image_small_url") or product.get("image_url")
                    
                    if image_url:
                        self._cache[cache_key] = image_url
                        return image_url
                
                # No image found
                self._cache[cache_key] = None
                return None
                
        except Exception as e:
            # Log error but don't fail - return None
            print(f"OpenFoodFacts image lookup failed for '{product_name}': {e}")
            return None
    
    async def get_product_images_batch(self, product_names: list[str]) -> dict[str, str | None]:
        """
        Fetch images for multiple products.
        
        Args:
            product_names: List of product names
            
        Returns:
            Dict mapping product name to image URL (or None)
        """
        results = {}
        for name in product_names:
            results[name] = await self.get_product_image(name)
        return results


# Singleton instance
_image_service: ImageService | None = None


def get_image_service() -> ImageService:
    """Get singleton ImageService instance."""
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service
