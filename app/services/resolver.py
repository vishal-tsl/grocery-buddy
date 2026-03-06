from app.models.schemas import (
    NormalizedItem,
    StructuredItem,
    AutocompleteProduct,
    ResolvedProduct,
    ProductOption,
    ConfidenceLevel,
    MatchSource,
    SuggestionType,
)
from app.services.autocomplete import get_autocomplete_client


class ProductResolver:
    """
    Deterministic product resolver with confidence scoring.
    
    This is NON-LLM logic that evaluates API results and applies safe fallbacks.
    Images are from BasketSavings only (Autocomplete API).
    """
    
    def __init__(self):
        self.autocomplete_client = get_autocomplete_client()
    
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
        
        # Build final structured item with safe fallbacks (images from BasketSavings only)
        return self._build_structured_item(normalized_item, resolved, search_query=search_query)
    
    def _build_search_query(self, normalized_item: NormalizedItem) -> str:
        """Build the search query from normalized item."""
        parts = [normalized_item.normalized_product_name]
        
        # Add modifiers that might help search (e.g., "2%", "organic")
        for modifier in normalized_item.modifiers:
            # Only add modifiers that are likely product descriptors
            if modifier.lower() not in ["maybe", "some", "idk"]:
                parts.append(modifier)
        
        return " ".join(parts)

    def _pick_best_suggestion(self, candidates: list[AutocompleteProduct]) -> AutocompleteProduct | None:
        """Always use the first option in API order so name, image and 'Option 1' match; avoids wrong fetch."""
        if not candidates:
            return None
        return candidates[0]

    def _match_reason(self, suggestion: AutocompleteProduct, match_source: MatchSource) -> str:
        """Build human-readable reason for network/UI: why mapped to product or keyword."""
        if match_source == MatchSource.PRODUCT and suggestion.sku and not suggestion.sku.startswith(("brand_", "type_", "item_")):
            return f"product (SKU {suggestion.sku}): {suggestion.name}"
        if match_source == MatchSource.KEYWORD:
            kind = "keyword (type)" if suggestion.suggestion_type == SuggestionType.KEYWORD else "keyword (match)"
            return f"{kind}: {suggestion.name}"
        return f"ai_text: {suggestion.name or 'no API match'}"

    def _brand_matches(self, normalized_item: NormalizedItem, suggestion: AutocompleteProduct) -> bool:
        """True if suggestion brand appears in user's input (safe to show this suggestion's image)."""
        if not suggestion.brand:
            return False
        user_text = normalized_item.normalized_product_name.lower()
        brand_lower = suggestion.brand.lower()
        if brand_lower in user_text or user_text in brand_lower:
            return True
        # Strip common suffixes so "The Happy Egg Co." -> "happy egg"
        stop = ("the ", " co.", " inc.", " llc.", " ltd.", " corp.")
        brand_core = brand_lower
        for s in stop:
            brand_core = brand_core.replace(s, " ")
        brand_core = " ".join(brand_core.split()).strip()
        if brand_core and brand_core in user_text:
            return True
        # Match when brand's first significant word is in user text (e.g. "Happy Egg" vs "Happy Egg Eggs")
        words = [w for w in brand_lower.split() if w not in ("the", "a", "an") and len(w) > 1]
        if not words:
            return False
        return words[0] in user_text or (len(words) >= 2 and (words[0] + " " + words[1]) in user_text)

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
            return ResolvedProduct(
                product_name=self._to_title_case(normalized_item.normalized_product_name),
                sku=None,
                category=None,
                image_url=None,
                brand=None,
                size=None,
                confidence=ConfidenceLevel.LOW,
                needs_specification=True,
                api_suggestions=[],
                match_source=MatchSource.AI_TEXT,
                match_reason="ai_text: no API results",
            )

        top_suggestions = suggestions[:3]
        search_terms = search_query.lower().split()
        normalized_name = normalized_item.normalized_product_name.lower()
        needs_specification = not user_specified_brand

        # HIGH: collect matches, prefer product-type so we get exact API name (e.g. "Natural Coconut Water Not from Concentrate")
        high_matches = []
        for s in top_suggestions:
            sn = s.name.lower()
            if normalized_name in sn or all(term in sn for term in search_terms if len(term) > 2):
                high_matches.append(s)
        if high_matches:
            suggestion = self._pick_best_suggestion(high_matches) or high_matches[0]
            # When any product/SKU is mapped, show exact API product name in the list
            product_name = suggestion.name
            if user_specified_brand:
                image_url = suggestion.image_url if self._brand_matches(normalized_item, suggestion) else None
            else:
                image_url = suggestion.image_url
            use_sku = suggestion.sku if user_specified_brand else (suggestion.sku if suggestion.suggestion_type == SuggestionType.PRODUCT and not suggestion.sku.startswith(("brand_", "type_", "item_")) else None)
            ms = MatchSource.PRODUCT if (use_sku and suggestion.suggestion_type == SuggestionType.PRODUCT) else MatchSource.KEYWORD
            return ResolvedProduct(
                product_name=product_name,
                sku=use_sku,
                category=suggestion.category,
                image_url=image_url,
                brand=suggestion.brand if not user_specified_brand else None,
                size=suggestion.size,
                confidence=ConfidenceLevel.HIGH,
                needs_specification=needs_specification,
                api_suggestions=suggestions,
                match_source=ms,
                match_reason=self._match_reason(suggestion, ms),
            )

        # MEDIUM: partial match, prefer product-type suggestion
        significant_terms = [t for t in search_terms if len(t) > 2]
        medium_matches = []
        for s in suggestions[:5]:
            sn = s.name.lower()
            if significant_terms and any(term in sn for term in significant_terms):
                medium_matches.append(s)
        if medium_matches:
            suggestion = self._pick_best_suggestion(medium_matches) or medium_matches[0]
            product_name = suggestion.name
            if user_specified_brand:
                image_url = suggestion.image_url if self._brand_matches(normalized_item, suggestion) else None
            else:
                image_url = suggestion.image_url
            ms = MatchSource.PRODUCT if suggestion.suggestion_type == SuggestionType.PRODUCT else MatchSource.KEYWORD
            return ResolvedProduct(
                product_name=product_name,
                sku=None,
                category=suggestion.category,
                image_url=image_url,
                brand=suggestion.brand if not user_specified_brand else None,
                size=suggestion.size,
                confidence=ConfidenceLevel.MEDIUM,
                needs_specification=not user_specified_brand,
                api_suggestions=suggestions,
                match_source=ms,
                match_reason=self._match_reason(suggestion, ms),
            )

        first_suggestion = self._pick_best_suggestion(suggestions[:5]) or suggestions[0]
        product_name = first_suggestion.name
        if user_specified_brand:
            image_url = first_suggestion.image_url if self._brand_matches(normalized_item, first_suggestion) else None
        else:
            image_url = first_suggestion.image_url
        ms = MatchSource.PRODUCT if first_suggestion.suggestion_type == SuggestionType.PRODUCT else MatchSource.KEYWORD
        return ResolvedProduct(
            product_name=product_name,
            sku=None,
            category=first_suggestion.category,
            image_url=image_url,
            brand=first_suggestion.brand if not user_specified_brand else None,
            size=first_suggestion.size,
            confidence=ConfidenceLevel.LOW,
            needs_specification=not user_specified_brand,
            api_suggestions=suggestions,
            match_source=ms,
            match_reason=self._match_reason(first_suggestion, ms),
        )
    
    def _build_structured_item(
        self,
        normalized_item: NormalizedItem,
        resolved: ResolvedProduct,
        *,
        search_query: str = "",
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
        
        # Build options from all autocomplete API suggestions (no cap – use full API response)
        options: list[ProductOption] = []
        selected_option_index = None
        base_product_name = normalized_item.normalized_product_name.lower()
        seen_skus: set[str] = set()

        def add_option(suggestion: AutocompleteProduct) -> None:
            if suggestion.sku in seen_skus or not suggestion.sku or not suggestion.name:
                return
            seen_skus.add(suggestion.sku)
            options.append(ProductOption(
                sku=suggestion.sku,
                name=suggestion.name,
                brand=suggestion.brand,
                image_url=suggestion.image_url
            ))

        # First pass: brand variations of the SAME product (e.g. "Kerrygold Butter" for "butter")
        for suggestion in resolved.api_suggestions:
            if not suggestion.sku or not suggestion.name or suggestion.brand is None:
                continue
            suggestion_name_lower = suggestion.name.lower()
            if base_product_name not in suggestion_name_lower:
                continue
            words_before = suggestion_name_lower.split(base_product_name)[0].strip()
            if words_before in ["peanut", "almond", "cashew", "sunflower", "apple", "coconut", "soy"]:
                continue
            add_option(suggestion)

        # Add all remaining API suggestions so options match full API result (e.g. 20)
        for suggestion in resolved.api_suggestions:
            add_option(suggestion)

        # Which option (1-based) was auto-selected
        for i, opt in enumerate(options):
            if resolved.sku and opt.sku == resolved.sku:
                selected_option_index = i + 1
                break
            if opt.name == product_name and (not resolved.brand or opt.brand == resolved.brand):
                selected_option_index = i + 1
                break

        # Index among the full 20 suggestions (for chip: "Option 3 of 20") – for both product and keyword
        selected_suggestion_index = None
        total_suggestions = len(resolved.api_suggestions) if resolved.api_suggestions else None
        if resolved.api_suggestions and product_name:
            for i, s in enumerate(resolved.api_suggestions):
                if s.name != product_name:
                    continue
                if resolved.sku and s.sku != resolved.sku:
                    continue
                selected_suggestion_index = i + 1
                break
        
        # If we have a selected option and no image yet, use that option's image so it's never null when options have images
        image_url = resolved.image_url
        if not image_url and selected_option_index and 1 <= selected_option_index <= len(options):
            image_url = options[selected_option_index - 1].image_url

        # Ensure brand is set when we have options so the UI can show brand names
        brand = resolved.brand
        if not brand and selected_option_index and 1 <= selected_option_index <= len(options):
            brand = options[selected_option_index - 1].brand
        if not brand and options:
            brand = options[0].brand
        if resolved.match_source == MatchSource.KEYWORD:
            brand = None
        
        category = self._pick_category(resolved)

        return StructuredItem(
            product_name=product_name,
            sku=resolved.sku if resolved.confidence == ConfidenceLevel.HIGH else None,
            quantity=normalized_item.quantity,
            unit=normalized_item.unit,
            category=category,
            image_url=image_url,
            brand=brand,
            size=resolved.size,
            notes=" | ".join(notes_parts) if notes_parts else "",
            needs_specification=resolved.needs_specification,
            options=options,
            match_source=resolved.match_source,
            match_reason=resolved.match_reason,
            confidence=self._confidence_to_score(resolved.confidence),
            selected_option_index=selected_option_index,
            selected_suggestion_index=selected_suggestion_index,
            total_suggestions=total_suggestions,
            autocomplete_query=search_query,
        )

    def _to_title_case(self, text: str) -> str:
        """Convert text to title case for clean product names."""
        if not text:
            return text
        return " ".join(word.capitalize() for word in text.split())

    def _pick_category(self, resolved: ResolvedProduct) -> str | None:
        """Pick the best available category from resolved product or suggestions."""
        if resolved.category:
            return resolved.category

        for suggestion in resolved.api_suggestions:
            if suggestion.category:
                return suggestion.category

        return None

    def _confidence_to_score(self, confidence: ConfidenceLevel) -> float:
        """Map internal confidence bands to numeric score for UI."""
        if confidence == ConfidenceLevel.HIGH:
            return 0.95
        if confidence == ConfidenceLevel.MEDIUM:
            return 0.75
        return 0.45
    
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
            structured_item = self._build_structured_item(normalized_item, resolved, search_query=search_queries[i])
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
