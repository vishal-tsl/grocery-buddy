from app.models.schemas import (
    NormalizedItem,
    StructuredItem,
    AutocompleteProduct,
    ResolvedProduct,
    ProductOption,
    ConfidenceLevel,
)
from app.services.autocomplete import get_autocomplete_client
from app.services.image_service import get_image_service


class ProductResolver:
    """
    Deterministic product resolver with confidence scoring.
    
    This is NON-LLM logic that evaluates API results and applies safe fallbacks.
    """
    
    def __init__(self):
        self.autocomplete_client = get_autocomplete_client()
        self.image_service = get_image_service()
    
    async def resolve(self, normalized_item: NormalizedItem) -> StructuredItem:
        """
        Resolve a normalized item to a structured output item.
        
        Uses Autocomplete API for product lookup, then applies deterministic
        confidence scoring to decide whether to accept the result.
        
        Args:
            normalized_item: The normalized grocery item
            
        Returns:
            StructuredItem conforming to the output contract
        """
        # Build search query from normalized name + modifiers
        search_query = self._build_search_query(normalized_item)
        
        # Call Autocomplete API
        suggestions = await self.autocomplete_client.search(search_query)
        
        # Brand options are included in the API response - no extra calls needed
        
        # Evaluate confidence and get resolved product
        resolved = self._evaluate_confidence(
            normalized_item=normalized_item,
            suggestions=suggestions,
            search_query=search_query
        )
        
        # Build final structured item with safe fallbacks
        structured_item = self._build_structured_item(normalized_item, resolved)
        
        # Fetch image from OpenFoodFacts for the main product only (options use API images)
        if not structured_item.image_url:
            openfoodfacts_image = await self.image_service.get_product_image(
                product_name=structured_item.product_name
            )
            if openfoodfacts_image:
                structured_item.image_url = openfoodfacts_image
        
        return structured_item
    
    def _build_search_query(self, normalized_item: NormalizedItem) -> str:
        """Build the search query from normalized item."""
        parts = [normalized_item.normalized_product_name]
        
        # Add modifiers that might help search (e.g., "2%", "organic")
        for modifier in normalized_item.modifiers:
            # Only add modifiers that are likely product descriptors
            if modifier.lower() not in ["maybe", "some", "idk"]:
                parts.append(modifier)
        
        return " ".join(parts)
    
    def _evaluate_confidence(
        self,
        normalized_item: NormalizedItem,
        suggestions: list[AutocompleteProduct],
        search_query: str
    ) -> ResolvedProduct:
        """
        Apply deterministic confidence scoring rules.
        
        Rules:
        - HIGH: Exact keyword match in top 3 results -> accept with SKU
        - MEDIUM: Category-level or partial match -> accept generic product name, no SKU
        - LOW: No meaningful match -> use generic name, move original to notes
        
        Brand Logic:
        - If user specified a brand (has_brand=True), don't show options
        - If NO brand specified, ALWAYS show options for user to choose
        """
        # Check if user specified a brand
        user_specified_brand = normalized_item.has_brand
        
        if not suggestions:
            # No results from API
            return ResolvedProduct(
                product_name=self._to_title_case(normalized_item.normalized_product_name),
                sku=None,
                category=None,
                image_url=None,
                brand=None,
                size=None,
                confidence=ConfidenceLevel.LOW,
                needs_specification=True,  # User should specify since no matches
                api_suggestions=[]
            )
        
        # Check top 3 results for strong match
        top_suggestions = suggestions[:3]
        search_terms = search_query.lower().split()
        normalized_name = normalized_item.normalized_product_name.lower()
        
        # If no brand specified, user should always see options to choose from
        # Only skip specification if user explicitly mentioned a brand
        needs_specification = not user_specified_brand
        
        for suggestion in top_suggestions:
            suggestion_name_lower = suggestion.name.lower()
            
            # HIGH confidence: normalized product name appears in suggestion name
            if normalized_name in suggestion_name_lower:
                # Use the API's product name (properly formatted, e.g., "Salted Butter")
                return ResolvedProduct(
                    product_name=suggestion.name,
                    sku=suggestion.sku if user_specified_brand else None,  # Only use SKU if brand specified
                    category=suggestion.category,
                    image_url=suggestion.image_url,
                    brand=suggestion.brand,
                    size=suggestion.size,
                    confidence=ConfidenceLevel.HIGH,
                    needs_specification=needs_specification,
                    api_suggestions=suggestions
                )
            
            # HIGH confidence: suggestion name contains all search terms
            if all(term in suggestion_name_lower for term in search_terms if len(term) > 2):
                return ResolvedProduct(
                    product_name=suggestion.name,
                    sku=suggestion.sku if user_specified_brand else None,
                    category=suggestion.category,
                    image_url=suggestion.image_url,
                    brand=suggestion.brand,
                    size=suggestion.size,
                    confidence=ConfidenceLevel.HIGH,
                    needs_specification=needs_specification,
                    api_suggestions=suggestions
                )
        
        # Check for partial/category match - use first suggestion's name for autocomplete
        for suggestion in suggestions[:5]:
            suggestion_name_lower = suggestion.name.lower()
            
            # MEDIUM confidence: at least one significant term matches
            significant_terms = [t for t in search_terms if len(t) > 2]
            if significant_terms and any(term in suggestion_name_lower for term in significant_terms):
                # Use the API's suggested name (autocomplete effect)
                return ResolvedProduct(
                    product_name=suggestion.name,  # Use API name for autocomplete
                    sku=None,  # Don't use SKU for partial matches
                    category=suggestion.category,
                    image_url=suggestion.image_url,
                    brand=suggestion.brand,
                    size=suggestion.size,
                    confidence=ConfidenceLevel.MEDIUM,
                    needs_specification=True,  # Medium confidence = user should verify
                    api_suggestions=suggestions
                )
        
        # LOW confidence: use first suggestion as autocomplete
        first_suggestion = suggestions[0]
        return ResolvedProduct(
            product_name=first_suggestion.name,  # Use API name for autocomplete
            sku=None,
            category=first_suggestion.category,
            image_url=first_suggestion.image_url,
            brand=first_suggestion.brand,
            size=first_suggestion.size,
            confidence=ConfidenceLevel.LOW,
            needs_specification=True,  # Low confidence = user should specify
            api_suggestions=suggestions
        )
    
    def _build_structured_item(
        self,
        normalized_item: NormalizedItem,
        resolved: ResolvedProduct
    ) -> StructuredItem:
        """
        Build the final structured item with safe fallbacks.
        
        Never invents SKUs - only uses SKU if from API and confidence is HIGH.
        Category is always included if available from API.
        """
        notes_parts = []
        
        # Add existing notes from normalization
        if normalized_item.notes:
            notes_parts.append(normalized_item.notes)
        
        # Add notes based on confidence
        if resolved.confidence == ConfidenceLevel.LOW:
            if not normalized_item.notes:  # Don't duplicate uncertainty notes
                notes_parts.append(f"Low confidence match for: '{normalized_item.original_text}'")
        
        # Use the resolved product name (already autocompleted from API)
        product_name = resolved.product_name
        
        # Only add modifiers if they're not already in the product name
        # This handles cases where API didn't include the modifier
        if normalized_item.modifiers:
            modifier_str = " ".join(normalized_item.modifiers)
            if modifier_str.lower() not in product_name.lower():
                # Check if any individual modifier is missing
                missing_modifiers = [
                    m for m in normalized_item.modifiers 
                    if m.lower() not in product_name.lower()
                ]
                if missing_modifiers:
                    product_name = f"{' '.join(missing_modifiers)} {product_name}".strip()
                    product_name = self._to_title_case(product_name)
        
        # Build product options from API suggestions
        # ONLY include brand variations of the SAME product (not different products)
        options = []
        base_product_name = normalized_item.normalized_product_name.lower()
        
        # First pass: collect brand options that match the base product
        brand_options = []
        for suggestion in resolved.api_suggestions:
            if not suggestion.sku or not suggestion.name:
                continue
            
            suggestion_name_lower = suggestion.name.lower()
            
            # Only include if:
            # 1. Has a brand AND
            # 2. Contains the base product name (e.g., "butter" in "Kerrygold Butter")
            #    but NOT a different product (e.g., "Peanut Butter" shouldn't match "butter")
            if suggestion.brand and base_product_name in suggestion_name_lower:
                # Exclude if it's a different product type
                # e.g., "Peanut Butter" should not be included when searching for "butter"
                words_before_product = suggestion_name_lower.split(base_product_name)[0].strip()
                if words_before_product not in ["peanut", "almond", "cashew", "sunflower", "apple", "coconut", "soy"]:
                    brand_options.append(ProductOption(
                        sku=suggestion.sku,
                        name=suggestion.name,
                        brand=suggestion.brand,
                        image_url=suggestion.image_url
                    ))
        
        # Use brand options if we have them, otherwise fall back to showing product types
        if brand_options:
            options = brand_options[:5]
        else:
            # No brand options available, show generic product types for user to narrow down
            for suggestion in resolved.api_suggestions[:5]:
                if suggestion.sku and suggestion.name:
                    options.append(ProductOption(
                        sku=suggestion.sku,
                        name=suggestion.name,
                        brand=suggestion.brand,
                        image_url=suggestion.image_url
                    ))
        
        return StructuredItem(
            product_name=product_name,
            sku=resolved.sku if resolved.confidence == ConfidenceLevel.HIGH else None,
            quantity=normalized_item.quantity,
            unit=normalized_item.unit,
            category=resolved.category,
            image_url=resolved.image_url,
            brand=resolved.brand,
            size=resolved.size,
            notes=" | ".join(notes_parts) if notes_parts else "",
            needs_specification=resolved.needs_specification,
            options=options
        )
    
    def _to_title_case(self, text: str) -> str:
        """Convert text to title case for clean product names."""
        if not text:
            return text
        return " ".join(word.capitalize() for word in text.split())
    
    async def resolve_batch(self, normalized_items: list[NormalizedItem]) -> list[StructuredItem]:
        """
        Resolve multiple normalized items with optimized parallel processing.
        
        Strategy:
        1. All Autocomplete API calls in parallel  
        2. Build structured items (no I/O)
        Images are NOT fetched here for speed - UI can load them lazily
        """
        import asyncio
        
        # Step 1: All API calls in parallel
        search_queries = [self._build_search_query(item) for item in normalized_items]
        api_tasks = [self.autocomplete_client.search(q) for q in search_queries]
        all_suggestions = await asyncio.gather(*api_tasks)
        
        # Step 2: Build structured items (CPU-bound, fast)
        structured_items = []
        for i, normalized_item in enumerate(normalized_items):
            suggestions = all_suggestions[i]
            resolved = self._evaluate_confidence(
                normalized_item=normalized_item,
                suggestions=suggestions,
                search_query=search_queries[i]
            )
            structured_item = self._build_structured_item(normalized_item, resolved)
            structured_items.append(structured_item)
        
        # Images are loaded by the API from Autocomplete response (no extra fetch needed)
        # If Autocomplete API doesn't have images, UI shows placeholder
        
        return structured_items


# Singleton instance
_resolver: ProductResolver | None = None


def get_resolver() -> ProductResolver:
    """Get or create resolver singleton."""
    global _resolver
    if _resolver is None:
        _resolver = ProductResolver()
    return _resolver
