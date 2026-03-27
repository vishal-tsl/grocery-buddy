import asyncio

from app.models.schemas import (
    NormalizedItem,
    StructuredItem,
    AutocompleteProduct,
    ResolvedProduct,
    ProductOption,
    ConfidenceLevel,
    MatchSource,
)
from app.services.autocomplete import get_autocomplete_client
from app.services.matching_pipeline import (
    build_retrieval_queries,
    evaluate_match,
    merge_suggestions,
    maybe_llm_rerank_sku,
)
from app.agents.normalizer import _sanitize_quantity


# Produce sizing confuses autocomplete ("tomatoes medium" → wrong SKUs); keep in modifiers for notes.
_SKIP_IN_SEARCH_MODIFIERS = frozenset({"small", "medium", "large"})


def _strip_as_written_note_fragments(notes: str) -> str:
    """Drop legacy / model-echoed 'As written:' fragments from normalizer notes."""
    if not notes or not notes.strip():
        return ""
    parts: list[str] = []
    for p in notes.split(" | "):
        t = p.strip()
        if not t:
            continue
        low = t.lower().lstrip("“\"'").strip()
        if low.startswith("as written"):
            continue
        parts.append(t)
    return " | ".join(parts)


class ProductResolver:
    """
    Product resolver: multi-query Autocomplete retrieval, context-aware scoring,
    optional LLM re-rank, calibrated confidence.
    """

    def __init__(self):
        self.autocomplete_client = get_autocomplete_client()

    async def resolve(self, normalized_item: NormalizedItem) -> StructuredItem:
        search_query, merged = await self._fetch_merged_suggestions(normalized_item)
        rerank_sku = await maybe_llm_rerank_sku(normalized_item, merged)
        resolved = evaluate_match(
            normalized_item, merged, search_query, reranked_first_sku=rerank_sku
        )
        return self._build_structured_item(normalized_item, resolved, search_query=search_query)

    async def _fetch_merged_suggestions(
        self, normalized_item: NormalizedItem
    ) -> tuple[str, list[AutocompleteProduct]]:
        search_query = self._build_search_query(normalized_item)
        queries = build_retrieval_queries(normalized_item, search_query)
        lists = await asyncio.gather(
            *[self.autocomplete_client.search(q) for q in queries]
        )
        merged = merge_suggestions(list(lists))
        if not merged:
            alternative_query = self._get_alternative_query(normalized_item)
            if alternative_query and alternative_query.strip():
                merged = await self.autocomplete_client.search(alternative_query)
                search_query = alternative_query
        return search_query, merged

    def _build_search_query(self, normalized_item: NormalizedItem) -> str:
        parts = [normalized_item.normalized_product_name]
        for modifier in normalized_item.modifiers:
            ml = modifier.lower()
            if ml in ["maybe", "some", "idk"]:
                continue
            if ml in _SKIP_IN_SEARCH_MODIFIERS:
                continue
            parts.append(modifier)
        return " ".join(parts)

    def _get_alternative_query(self, normalized_item: NormalizedItem) -> str | None:
        name = normalized_item.normalized_product_name.lower()
        all_text = (name + " " + " ".join(normalized_item.modifiers)).lower()
        synonyms = {
            "protein-enriched": "high protein",
            "full-fat": "whole milk",
            "full fat": "whole milk",
        }
        if any(x in all_text for x in ["yogurt", "skyr", "milk", "cheese"]):
            synonyms["full-fat"] = "5%" if "yogurt" in all_text else "whole"
            synonyms["low-fat"] = "2%"
            synonyms["non-fat"] = "0%"
        for key, val in synonyms.items():
            if key in all_text:
                return all_text.replace(key, val)
        return None

    def _build_structured_item(
        self,
        normalized_item: NormalizedItem,
        resolved: ResolvedProduct,
        *,
        search_query: str = "",
    ) -> StructuredItem:
        notes_parts: list[str] = []
        if normalized_item.notes:
            cleaned_notes = _strip_as_written_note_fragments(normalized_item.notes)
            if cleaned_notes:
                notes_parts.append(cleaned_notes)

        if resolved.confidence == ConfidenceLevel.LOW:
            if not normalized_item.notes:
                notes_parts.append(
                    f"Low confidence match for: '{normalized_item.original_text}'"
                )

        product_name = resolved.product_name

        if normalized_item.modifiers:
            missing_modifiers = [
                m
                for m in normalized_item.modifiers
                if m.lower() not in product_name.lower()
                and m.lower() not in _SKIP_IN_SEARCH_MODIFIERS
            ]
            if missing_modifiers:
                notes_parts.append(
                    "Includes: " + ", ".join(missing_modifiers)
                )

        options: list[ProductOption] = []
        selected_option_index = None
        seen_skus: set[str] = set()

        def add_option(suggestion: AutocompleteProduct) -> None:
            if suggestion.sku in seen_skus or not suggestion.sku or not suggestion.name:
                return
            seen_skus.add(suggestion.sku)
            options.append(
                ProductOption(
                    sku=suggestion.sku,
                    name=suggestion.name,
                    brand=suggestion.brand,
                    image_url=suggestion.image_url,
                )
            )

        for suggestion in resolved.api_suggestions:
            if not suggestion.sku or not suggestion.name:
                continue
            add_option(suggestion)

        for i, opt in enumerate(options):
            if resolved.sku and opt.sku == resolved.sku:
                selected_option_index = i + 1
                break
            if opt.name == product_name and (
                not resolved.brand or opt.brand == resolved.brand
            ):
                selected_option_index = i + 1
                break

        selected_suggestion_index = None
        total_suggestions = (
            len(resolved.api_suggestions) if resolved.api_suggestions else None
        )
        if resolved.api_suggestions and product_name:
            for i, s in enumerate(resolved.api_suggestions):
                if s.name != product_name:
                    continue
                if resolved.sku and s.sku != resolved.sku:
                    continue
                selected_suggestion_index = i + 1
                break

        image_url = resolved.image_url
        brand = resolved.brand
        m_source = str(
            resolved.match_source.value
            if hasattr(resolved.match_source, "value")
            else resolved.match_source
        ).lower()

        print(f"DEBUG: Resolving '{product_name}' Source='{m_source}' Image='{image_url}'")

        if resolved.match_source == MatchSource.KEYWORD:
            brand = None
            # Use only the keyword/type row's own image from the API — no borrow from brand options.
        elif "product" in m_source:
            if not image_url and selected_option_index and 1 <= selected_option_index <= len(
                options
            ):
                image_url = options[selected_option_index - 1].image_url
            if not brand and selected_option_index and 1 <= selected_option_index <= len(
                options
            ):
                brand = options[selected_option_index - 1].brand
            if "product" in m_source and not brand and options:
                brand = options[0].brand

        category = self._pick_category(resolved)

        conf_display = (
            resolved.confidence_numeric
            if resolved.confidence_numeric is not None
            else self._confidence_to_score(resolved.confidence)
        )

        qty_out = _sanitize_quantity(
            normalized_item.original_text or "",
            normalized_item.quantity,
            unit=normalized_item.unit,
            product_name=normalized_item.normalized_product_name,
        )

        return StructuredItem(
            product_name=product_name,
            sku=resolved.sku if resolved.confidence == ConfidenceLevel.HIGH else None,
            quantity=qty_out,
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
            confidence=conf_display,
            confidence_tier=resolved.confidence,
            selected_option_index=selected_option_index,
            selected_suggestion_index=selected_suggestion_index,
            total_suggestions=total_suggestions,
            autocomplete_query=search_query,
        )

    def _to_title_case(self, text: str) -> str:
        if not text:
            return text
        return " ".join(word.capitalize() for word in text.split())

    def _pick_category(self, resolved: ResolvedProduct) -> str | None:
        if resolved.category:
            return resolved.category
        for suggestion in resolved.api_suggestions:
            if suggestion.category:
                return suggestion.category
        return None

    def _confidence_to_score(self, confidence: ConfidenceLevel) -> float:
        if confidence == ConfidenceLevel.HIGH:
            return 0.95
        if confidence == ConfidenceLevel.MEDIUM:
            return 0.75
        return 0.45

    async def resolve_batch(
        self, normalized_items: list[NormalizedItem]
    ) -> list[StructuredItem]:
        fetched = await asyncio.gather(
            *[self._fetch_merged_suggestions(item) for item in normalized_items]
        )
        rerank_tasks = [
            maybe_llm_rerank_sku(item, merged) for item, (_, merged) in zip(normalized_items, fetched)
        ]
        reranks = await asyncio.gather(*rerank_tasks)

        structured_items: list[StructuredItem] = []
        for i, normalized_item in enumerate(normalized_items):
            search_query, merged = fetched[i]
            resolved = evaluate_match(
                normalized_item,
                merged,
                search_query,
                reranked_first_sku=reranks[i],
            )
            structured_items.append(
                self._build_structured_item(
                    normalized_item, resolved, search_query=search_query
                )
            )
        return structured_items


_resolver: ProductResolver | None = None


def get_resolver() -> ProductResolver:
    global _resolver
    if _resolver is None:
        _resolver = ProductResolver()
    return _resolver
