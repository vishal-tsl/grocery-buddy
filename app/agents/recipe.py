"""
Recipe Agent - Extracts ingredients from recipe names or URLs.

Supports:
1. Recipe names (e.g., "Chicken Alfredo", "Beef Tacos")
2. Recipe URLs from popular sites (AllRecipes, Food Network, etc.)
"""

import json
import re
import httpx
from google import genai
from app.config import get_settings


RECIPE_EXTRACTION_PROMPT = """You are a recipe ingredient extractor. Given a recipe name, generate a realistic, complete ingredient list.

RULES:
1. Include ALL typical ingredients for the dish (don't skip basics like salt, oil, etc.)
2. Include realistic quantities and units
3. Use specific product names (e.g., "chicken breast" not just "chicken")
4. Include brand names ONLY for products that are typically branded (e.g., "Parmesan cheese", not generic "cheese")
5. Be specific about cuts, types, and varieties
6. Format each ingredient as: "quantity unit ingredient" (e.g., "2 lbs chicken breast")

OUTPUT FORMAT:
Return a JSON object:
{
  "recipe_name": "Full recipe name",
  "servings": number,
  "ingredients": [
    "1 lb ground beef",
    "2 tablespoons olive oil",
    ...
  ]
}

EXAMPLES:

Recipe: "Spaghetti Carbonara"
{
  "recipe_name": "Spaghetti Carbonara",
  "servings": 4,
  "ingredients": [
    "1 lb spaghetti",
    "8 oz pancetta or guanciale",
    "4 large eggs",
    "1 cup Pecorino Romano cheese, grated",
    "1/2 cup Parmesan cheese, grated",
    "2 cloves garlic",
    "2 tablespoons olive oil",
    "1 teaspoon black pepper",
    "salt to taste"
  ]
}

Recipe: "Chicken Tikka Masala"
{
  "recipe_name": "Chicken Tikka Masala",
  "servings": 4,
  "ingredients": [
    "1.5 lbs boneless chicken thighs",
    "1 cup plain yogurt",
    "2 tablespoons lemon juice",
    "2 teaspoons garam masala",
    "1 teaspoon turmeric",
    "1 teaspoon cumin",
    "1 teaspoon paprika",
    "1/2 teaspoon cayenne pepper",
    "4 cloves garlic, minced",
    "1 inch fresh ginger, grated",
    "1 can (14 oz) crushed tomatoes",
    "1 cup heavy cream",
    "1 medium onion, diced",
    "2 tablespoons butter",
    "2 tablespoons vegetable oil",
    "fresh cilantro for garnish",
    "salt to taste"
  ]
}
"""


URL_EXTRACTION_PROMPT = """You are a recipe ingredient extractor. Given HTML content from a recipe webpage, extract the ingredients list.

RULES:
1. Extract ALL ingredients mentioned in the recipe
2. Preserve exact quantities and units as written
3. Clean up any HTML artifacts or formatting issues
4. If ingredients have notes (like "divided" or "optional"), include them
5. Combine duplicate ingredients if they appear multiple times

OUTPUT FORMAT:
Return a JSON object:
{
  "recipe_name": "Recipe title from the page",
  "servings": number (if found, else null),
  "source_url": "original URL",
  "ingredients": [
    "ingredient 1 as written",
    "ingredient 2 as written",
    ...
  ]
}

Extract ingredients from this HTML content:
"""


class RecipeAgent:
    """Extracts ingredients from recipe names or URLs."""
    
    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_id = "gemini-2.0-flash"
        self.http_client = httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    def extract_from_name(self, recipe_name: str) -> dict:
        """
        Generate ingredient list from a recipe name using LLM.
        
        Args:
            recipe_name: Name of the dish (e.g., "Chicken Alfredo")
            
        Returns:
            Dict with recipe_name, servings, and ingredients list
        """
        prompt = f"""{RECIPE_EXTRACTION_PROMPT}

Now generate ingredients for this recipe:

Recipe: "{recipe_name}"

Return ONLY the JSON object, no other text."""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={"temperature": 0.3}  # Slight creativity for recipes
            )
            response_text = response.text.strip()
            
            # Clean up response
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            data = json.loads(response_text)
            return {
                "recipe_name": data.get("recipe_name", recipe_name),
                "servings": data.get("servings"),
                "ingredients": data.get("ingredients", []),
                "source": "generated"
            }
            
        except Exception as e:
            print(f"Recipe extraction failed: {e}")
            return {
                "recipe_name": recipe_name,
                "servings": None,
                "ingredients": [],
                "error": str(e)
            }
    
    async def extract_from_url(self, url: str) -> dict:
        """
        Extract ingredients from a recipe URL by scraping the page.
        
        Args:
            url: URL to a recipe page
            
        Returns:
            Dict with recipe_name, servings, source_url, and ingredients list
        """
        try:
            # Fetch the webpage
            response = await self.http_client.get(url, follow_redirects=True)
            response.raise_for_status()
            html_content = response.text
            
            # Try to extract structured data first (JSON-LD)
            structured_data = self._extract_json_ld(html_content)
            if structured_data and structured_data.get("ingredients"):
                return {
                    "recipe_name": structured_data.get("name", "Recipe"),
                    "servings": structured_data.get("servings"),
                    "source_url": url,
                    "ingredients": structured_data["ingredients"],
                    "source": "structured_data"
                }
            
            # Fall back to LLM extraction
            # Truncate HTML to avoid token limits
            clean_html = self._clean_html(html_content)
            truncated = clean_html[:15000]  # ~4K tokens
            
            prompt = f"""{URL_EXTRACTION_PROMPT}

URL: {url}

HTML Content:
{truncated}

Return ONLY the JSON object, no other text."""

            llm_response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={"temperature": 0}
            )
            response_text = llm_response.text.strip()
            
            # Clean up response
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            data = json.loads(response_text)
            return {
                "recipe_name": data.get("recipe_name", "Recipe"),
                "servings": data.get("servings"),
                "source_url": url,
                "ingredients": data.get("ingredients", []),
                "source": "extracted"
            }
            
        except httpx.HTTPError as e:
            print(f"Failed to fetch URL: {e}")
            return {
                "recipe_name": "Unknown",
                "source_url": url,
                "ingredients": [],
                "error": f"Failed to fetch URL: {str(e)}"
            }
        except Exception as e:
            print(f"Recipe URL extraction failed: {e}")
            return {
                "recipe_name": "Unknown",
                "source_url": url,
                "ingredients": [],
                "error": str(e)
            }
    
    def _extract_json_ld(self, html: str) -> dict | None:
        """Extract recipe data from JSON-LD structured data if present."""
        try:
            # Find JSON-LD script tags
            pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    
                    # Handle @graph format
                    if "@graph" in data:
                        data = data["@graph"]
                    
                    # Handle array format
                    if isinstance(data, list):
                        for item in data:
                            if item.get("@type") == "Recipe":
                                data = item
                                break
                        else:
                            continue
                    
                    # Check if it's a recipe
                    if data.get("@type") == "Recipe":
                        ingredients = data.get("recipeIngredient", [])
                        
                        # Clean up ingredients
                        if ingredients:
                            return {
                                "name": data.get("name"),
                                "servings": self._parse_yield(data.get("recipeYield")),
                                "ingredients": ingredients
                            }
                except json.JSONDecodeError:
                    continue
            
            return None
            
        except Exception as e:
            print(f"JSON-LD extraction failed: {e}")
            return None
    
    def _parse_yield(self, yield_value) -> int | None:
        """Parse recipe yield/servings from various formats."""
        if not yield_value:
            return None
        
        if isinstance(yield_value, int):
            return yield_value
        
        if isinstance(yield_value, str):
            # Try to extract number
            numbers = re.findall(r'\d+', yield_value)
            if numbers:
                return int(numbers[0])
        
        if isinstance(yield_value, list) and yield_value:
            return self._parse_yield(yield_value[0])
        
        return None
    
    def _clean_html(self, html: str) -> str:
        """Remove scripts, styles, and unnecessary HTML for LLM processing."""
        # Remove script and style tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # Remove excessive whitespace
        html = re.sub(r'\s+', ' ', html)
        
        return html
    
    def is_url(self, text: str) -> bool:
        """Check if the input is a URL."""
        url_pattern = r'^https?://[^\s]+$'
        return bool(re.match(url_pattern, text.strip()))


# Singleton instance
_recipe_agent: RecipeAgent | None = None


def get_recipe_agent() -> RecipeAgent:
    """Get or create recipe agent singleton."""
    global _recipe_agent
    if _recipe_agent is None:
        _recipe_agent = RecipeAgent()
    return _recipe_agent
