"""
Context-aware retrieval scoring, generic-vs-brand guardrails, and calibrated confidence.
Used by ProductResolver after multi-query Autocomplete merge.
"""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

from app.config import get_settings
from app.models.schemas import (
    AutocompleteProduct,
    ConfidenceLevel,
    ItemIntent,
    MatchSource,
    NormalizedItem,
    ResolvedProduct,
    SuggestionType,
)

# Single-token (or primary) product words that must not map to a branded SKU without strong evidence
GENERIC_LEXICON: frozenset[str] = frozenset({
    "eggs", "egg", "milk", "butter", "cheese", "bread", "flour", "sugar", "salt", "pepper",
    "oil", "rice", "pasta", "chicken", "beef", "pork", "fish", "onion", "garlic", "tomato",
    "tomatoes", "cucumber", "cucumbers", "bell", "avocado", "avocados", "salmon", "asparagus",
    "apple", "banana", "orange", "potato", "carrot", "lettuce", "spinach", "yogurt", "cream",
    "water", "juice", "coffee", "tea", "beans", "nuts", "honey", "vinegar", "sauce", "soup",
    "shrimp", "turkey", "bacon", "sausage", "mushroom", "lime", "lemon", "cilantro", "parsley",
    "cereal", "chips", "crackers", "tortillas", "shells", "tortilla", "mayo", "ketchup",
})

AMBIGUOUS_TERMS: frozenset[str] = frozenset({
    "shells", "sauce", "chips", "meat", "noodles", "herbs", "spices", "cheese", "milk",
})

CONTEXT_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "for", "with", "from", "get", "some", "any", "need",
    "want", "add", "buy", "please", "recipe", "ingredients", "about", "into", "this", "that",
})

PASTA_CATEGORY_HINTS: frozenset[str] = frozenset({"pasta", "noodle", "macaroni", "spaghetti", "italian"})
MEXICAN_CATEGORY_HINTS: frozenset[str] = frozenset({"mexican", "taco", "latino", "hispanic", "burrito"})
TACO_CONTEXT_BOOST: frozenset[str] = frozenset({"taco", "tacos", "burrito", "fajita", "mexican", "quesadilla"})


def _nfkc_lower(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").lower()


def word_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9%]+", _nfkc_lower(text))


def extract_context_tokens(prompt_context: str | None, max_tokens: int = 6) -> list[str]:
    if not prompt_context or not prompt_context.strip():
        return []
    toks = [t for t in word_tokens(prompt_context) if t not in CONTEXT_STOPWORDS and len(t) > 1]
    seen: set[str] = set()
    out: list[str] = []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= max_tokens:
            break
    return out


def merge_suggestions(lists: list[list[AutocompleteProduct]]) -> list[AutocompleteProduct]:
    """Merge API result lists, deduping by sku, preserving first-seen order (best rank wins)."""
    seen: set[str] = set()
    merged: list[AutocompleteProduct] = []
    for lst in lists:
        for s in lst:
            if s.sku in seen:
                continue
            seen.add(s.sku)
            merged.append(s)
    return merged


def build_retrieval_queries(normalized_item: NormalizedItem, primary_query: str) -> list[str]:
    """Primary + context-augmented variant queries."""
    queries: list[str] = []
    q = primary_query.strip()
    if q:
        queries.append(q)

    ctx = extract_context_tokens(normalized_item.prompt_context, max_tokens=4)
    item_toks = set(
        word_tokens(
            f"{normalized_item.normalized_product_name} {' '.join(normalized_item.modifiers)}"
        )
    )
    ambiguous_line = (
        _ambiguous_head(normalized_item)
        or normalized_item.item_intent == ItemIntent.AMBIGUOUS
    )
    if ctx and q and (item_toks.intersection(ctx) or ambiguous_line):
        # Prepend list context when it overlaps this line, or when the line is ambiguous
        # (e.g. "shells" + taco context). Skip for long monologues where early brands would
        # poison unrelated items (e.g. "Häagen-Dazs … tomatoes").
        augmented = f"{' '.join(ctx[:2])} {q}".strip()
        if augmented.lower() != q.lower():
            queries.append(augmented)

    if normalized_item.has_brand and q:
        # Second query without leading brand tokens (catalog may index under product name)
        toks = q.split()
        if len(toks) >= 3:
            stripped = " ".join(toks[1:]).strip()
            if stripped and stripped.lower() != q.lower():
                queries.append(stripped)

    if not normalized_item.has_brand and q:
        gq = f"{q} grocery".strip()
        if gq.lower() != q.lower():
            queries.append(gq)

    # Dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for x in queries:
        k = x.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def _infer_intent(item: NormalizedItem) -> ItemIntent:
    if item.item_intent:
        return item.item_intent
    if item.has_brand:
        return ItemIntent.BRANDED
    toks = word_tokens(item.normalized_product_name)
    if any(t in AMBIGUOUS_TERMS for t in toks):
        return ItemIntent.AMBIGUOUS
    if toks and all(t in GENERIC_LEXICON for t in toks):
        return ItemIntent.GENERIC
    return ItemIntent.GENERIC if len(toks) <= 2 else ItemIntent.AMBIGUOUS


def _is_hyper_generic(item: NormalizedItem) -> bool:
    toks = word_tokens(item.normalized_product_name)
    if not toks:
        return False
    return all(t in GENERIC_LEXICON for t in toks) and not item.has_brand


def _ambiguous_head(item: NormalizedItem) -> bool:
    toks = word_tokens(item.normalized_product_name)
    if not toks:
        return False
    if any(t in AMBIGUOUS_TERMS for t in toks):
        return True
    return len(toks) == 1 and toks[0] in AMBIGUOUS_TERMS


def _category_blob(suggestion: AutocompleteProduct) -> str:
    return _nfkc_lower(f"{suggestion.name} {suggestion.category or ''}")


def _has_pasta_signal(blob: str) -> bool:
    return any(h in blob for h in PASTA_CATEGORY_HINTS)


def _has_mexican_signal(blob: str) -> bool:
    return any(h in blob for h in MEXICAN_CATEGORY_HINTS) or "taco" in blob or "tortilla" in blob


def _conflicting_category_families(a: AutocompleteProduct, b: AutocompleteProduct) -> bool:
    ba, bb = _category_blob(a), _category_blob(b)
    pa, pb = _has_pasta_signal(ba), _has_pasta_signal(bb)
    ma, mb = _has_mexican_signal(ba), _has_mexican_signal(bb)
    return (pa and mb) or (pb and ma)


def _catalog_mismatch_penalty(
    item: NormalizedItem,
    suggestion: AutocompleteProduct,
) -> float:
    """
    Down-rank obvious wrong-category catalog hits (fresh produce vs canned/prepared).
    """
    pen = 0.0
    blob = _nfkc_lower(f"{suggestion.name} {suggestion.category or ''}")
    ut = _nfkc_lower(f"{item.normalized_product_name} {' '.join(item.modifiers)}")
    utoks = set(word_tokens(ut))

    # Fresh "tomatoes" vs tomato *products* (paste, sauce) — only guard the produce case.
    tomato_adjacent = bool(utoks & {"tomato", "tomatoes"})
    tomato_product_line = bool(
        utoks & {"paste", "sauce", "crushed", "puree", "soup", "rotel", "ketchup"}
    )
    wants_fresh_tomatoes = tomato_adjacent and not tomato_product_line
    if wants_fresh_tomatoes:
        if any(x in blob for x in ("rotel", "chiles", "chile", "with green")) and not any(
            x in ut for x in ("rotel", "chile", "chiles", "diced", "can", "canned")
        ):
            pen += 0.58
        if "canned" in blob and "canned" not in ut and "can " not in ut:
            pen += 0.32

    if "chicken" in utoks and "breast" in utoks:
        if "canned" in blob or " canned " in f" {blob} ":
            pen += 0.62

    wants_bell = "bell" in utoks and "pepper" in utoks
    if wants_bell and "relish" in blob and "relish" not in utoks:
        pen += 0.65

    return pen


def _context_adjust_score(
    suggestion: AutocompleteProduct,
    context_tokens: list[str],
) -> float:
    delta = 0.0
    blob = _nfkc_lower(f"{suggestion.name} {suggestion.category or ''} {suggestion.brand or ''}")
    if not context_tokens:
        return 0.0

    if any(t in TACO_CONTEXT_BOOST for t in context_tokens):
        if "taco" in blob or "tortilla" in blob or "corn shell" in blob or "hard shell" in blob:
            delta += 0.14
        cat = (suggestion.category or "").lower()
        if any(h in cat for h in PASTA_CATEGORY_HINTS) and "taco" not in blob:
            delta -= 0.12

    for t in context_tokens:
        if len(t) > 2 and t in blob:
            delta += 0.04
    return delta


def _score_suggestion(
    item: NormalizedItem,
    suggestion: AutocompleteProduct,
    search_query: str,
    rank_index: int,
    context_tokens: list[str],
) -> float:
    intent = _infer_intent(item)
    q = _nfkc_lower(search_query)
    name = _nfkc_lower(suggestion.name)
    user_line = _nfkc_lower(item.normalized_product_name)
    q_toks = word_tokens(search_query + " " + item.normalized_product_name + " " + " ".join(item.modifiers))
    name_toks = set(word_tokens(suggestion.name))

    coverage = 0.0
    if q_toks:
        hits = sum(1 for t in q_toks if t in name_toks)
        coverage = hits / len(q_toks)

    position_prior = 1.0 / (1.0 + rank_index * 0.08)
    fuzzy = fuzz.token_sort_ratio(user_line, name) / 100.0
    partial = fuzz.partial_ratio(user_line, name) / 100.0
    score = 0.28 * coverage + 0.22 * fuzzy + 0.12 * partial + 0.18 * position_prior

    score += _context_adjust_score(suggestion, context_tokens)
    score -= _catalog_mismatch_penalty(item, suggestion)

    if intent == ItemIntent.BRANDED or item.has_brand:
        score += 0.08 * (fuzz.QRatio(user_line, name) / 100.0)

    if _is_hyper_generic(item):
        if suggestion.suggestion_type == SuggestionType.KEYWORD:
            if name_toks >= set(word_tokens(item.normalized_product_name)) or user_line in name:
                score += 0.42
        elif suggestion.suggestion_type == SuggestionType.PRODUCT:
            # Penalize branded SKUs for "eggs", "milk", etc.
            extra_words = name_toks - set(word_tokens(item.normalized_product_name))
            if len(extra_words) >= 1 and coverage < 0.85:
                score -= 0.48
            elif fuzzy < 0.88:
                score -= 0.25
            if suggestion.brand and not _brand_matches(item, suggestion):
                score -= 0.55

    if _ambiguous_head(item):
        score -= 0.18

    if suggestion.suggestion_type == SuggestionType.KEYWORD and not _is_hyper_generic(item):
        score += 0.02  # slight preference for type rows when not hyper-generic

    return score


def _tier_from_internal(internal: float) -> ConfidenceLevel:
    if internal >= 0.78:
        return ConfidenceLevel.HIGH
    if internal >= 0.52:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _display_confidence(internal: float, tier: ConfidenceLevel) -> float:
    """Map internal score to UI range ~[0.35, 0.95], never flat 0.95 unless truly strong."""
    clamped = max(0.0, min(1.0, internal))
    base = 0.35 + clamped * 0.52
    if tier == ConfidenceLevel.HIGH and clamped < 0.92:
        base = min(base, 0.88)
    if tier == ConfidenceLevel.MEDIUM:
        base = min(base, 0.78)
    if tier == ConfidenceLevel.LOW:
        base = min(base, 0.58)
    return round(base, 2)


def _match_reason(suggestion: AutocompleteProduct, match_source: MatchSource) -> str:
    if match_source == MatchSource.PRODUCT and suggestion.sku and not suggestion.sku.startswith(("brand_", "type_", "item_")):
        return f"product (SKU {suggestion.sku}): {suggestion.name}"
    if match_source == MatchSource.KEYWORD:
        kind = "keyword (type)" if suggestion.suggestion_type == SuggestionType.KEYWORD else "keyword (match)"
        return f"{kind}: {suggestion.name}"
    return f"ai_text: {suggestion.name or 'no API match'}"


def _brand_matches(item: NormalizedItem, suggestion: AutocompleteProduct) -> bool:
    if not suggestion.brand:
        return False
    user_text = _nfkc_lower(item.normalized_product_name)
    brand_lower = _nfkc_lower(suggestion.brand)
    if brand_lower in user_text or user_text in brand_lower:
        return True
    stop = ("the ", " co.", " inc.", " llc.", " ltd.", " corp.")
    brand_core = brand_lower
    for s in stop:
        brand_core = brand_core.replace(s, " ")
    brand_core = " ".join(brand_core.split()).strip()
    if brand_core and brand_core in user_text:
        return True
    words = [w for w in brand_lower.split() if w not in ("the", "a", "an") and len(w) > 1]
    if not words:
        return False
    return words[0] in user_text or (len(words) >= 2 and (words[0] + " " + words[1]) in user_text)


def evaluate_match(
    normalized_item: NormalizedItem,
    suggestions: list[AutocompleteProduct],
    search_query: str,
    reranked_first_sku: str | None = None,
) -> ResolvedProduct:
    """
    Pick best candidate, calibrated confidence, and match metadata.
    If reranked_first_sku is set, that suggestion is moved to front before scoring merge.
    """
    user_specified_brand = normalized_item.has_brand
    needs_specification = not user_specified_brand

    if not suggestions:
        return ResolvedProduct(
            product_name=_title_case_safe(normalized_item.normalized_product_name),
            sku=None,
            category=None,
            image_url=None,
            brand=None,
            size=None,
            confidence=ConfidenceLevel.LOW,
            confidence_numeric=0.38,
            needs_specification=True,
            api_suggestions=[],
            match_source=MatchSource.AI_TEXT,
            match_reason="ai_text: no API results",
        )

    ordered = list(suggestions)
    if reranked_first_sku:
        for i, s in enumerate(ordered):
            if s.sku == reranked_first_sku:
                ordered = [s] + [x for j, x in enumerate(ordered) if j != i]
                break

    context_tokens = extract_context_tokens(normalized_item.prompt_context)

    scored: list[tuple[float, int, AutocompleteProduct]] = []
    for i, s in enumerate(ordered):
        sc = _score_suggestion(normalized_item, s, search_query, i, context_tokens)
        scored.append((sc, i, s))

    scored.sort(key=lambda x: (-x[0], x[1]))
    best_score, _, winner = scored[0]

    category_conflict = False
    if len(scored) >= 2:
        _, _, first = scored[0]
        _, _, second = scored[1]
        if _conflicting_category_families(first, second):
            category_conflict = True

    internal = max(0.0, min(1.0, best_score))
    if _ambiguous_head(normalized_item):
        internal *= 0.82
    if category_conflict:
        internal = min(internal, 0.62)
    tier = _tier_from_internal(internal)
    conf_num = _display_confidence(internal, tier)
    if category_conflict:
        conf_num = min(conf_num, 0.72)
        if tier == ConfidenceLevel.HIGH:
            tier = ConfidenceLevel.MEDIUM

    # Generic guard: never HIGH + branded PRODUCT for hyper-generic one-word
    if _is_hyper_generic(normalized_item) and winner.suggestion_type == SuggestionType.PRODUCT:
        kw = next((s for _, __, s in scored if s.suggestion_type == SuggestionType.KEYWORD), None)
        if kw:
            winner = kw
            internal = max(0.0, min(1.0, best_score - 0.12))
            if category_conflict:
                internal = min(internal, 0.62)
            tier = _tier_from_internal(internal)
            conf_num = _display_confidence(internal, tier)
            if category_conflict:
                conf_num = min(conf_num, 0.72)

    user_line_norm = _nfkc_lower(normalized_item.normalized_product_name)
    win_name_norm = _nfkc_lower(winner.name)

    if _is_hyper_generic(normalized_item) and winner.suggestion_type == SuggestionType.PRODUCT:
        if winner.brand and not _brand_matches(normalized_item, winner):
            return ResolvedProduct(
                product_name=normalized_item.normalized_product_name,
                sku=None,
                category=winner.category,
                image_url=None,
                brand=None,
                size=winner.size,
                confidence=ConfidenceLevel.LOW,
                confidence_numeric=min(0.55, _display_confidence(0.45, ConfidenceLevel.LOW)),
                needs_specification=True,
                api_suggestions=suggestions,
                match_source=MatchSource.AI_TEXT,
                match_reason="ai_text: generic item; best catalog hit is a branded SKU",
            )

    def _real_product_sku(sku: str | None) -> bool:
        return bool(sku) and not sku.startswith(("brand_", "type_", "item_"))

    use_sku: str | None = None
    if tier == ConfidenceLevel.HIGH and winner.suggestion_type == SuggestionType.PRODUCT and _real_product_sku(winner.sku):
        if user_specified_brand:
            if _brand_matches(normalized_item, winner):
                use_sku = winner.sku
        elif not _is_hyper_generic(normalized_item):
            use_sku = winner.sku
        elif fuzz.token_sort_ratio(user_line_norm, win_name_norm) >= 92:
            use_sku = winner.sku

    if winner.suggestion_type == SuggestionType.KEYWORD or not use_sku:
        ms = MatchSource.KEYWORD
    else:
        ms = MatchSource.PRODUCT

    branded_strong_keyword = (
        user_specified_brand
        and winner.suggestion_type == SuggestionType.KEYWORD
        and fuzz.token_sort_ratio(user_line_norm, win_name_norm) >= 72
    )

    image_url: str | None = None
    if ms == MatchSource.PRODUCT:
        image_url = winner.image_url if (not user_specified_brand or _brand_matches(normalized_item, winner)) else None
    else:
        image_url = winner.image_url

    if not user_specified_brand and (
        normalized_item.item_intent == ItemIntent.AMBIGUOUS
        or _infer_intent(normalized_item) == ItemIntent.AMBIGUOUS
    ):
        if fuzz.token_sort_ratio(user_line_norm, win_name_norm) < 95:
            conf_num = min(conf_num, 0.72)
            if tier == ConfidenceLevel.HIGH:
                tier = ConfidenceLevel.MEDIUM
            use_sku = None

    if _ambiguous_head(normalized_item):
        tier = ConfidenceLevel.MEDIUM if tier == ConfidenceLevel.HIGH else tier
        conf_num = min(conf_num, 0.76)
        use_sku = None
        ms = MatchSource.KEYWORD
        image_url = winner.image_url

    if tier == ConfidenceLevel.HIGH and ms == MatchSource.KEYWORD and not branded_strong_keyword:
        tier = ConfidenceLevel.MEDIUM
        conf_num = min(conf_num, 0.76)
        use_sku = None
        image_url = winner.image_url

    needs_out = needs_specification if ms != MatchSource.AI_TEXT else True
    if branded_strong_keyword:
        needs_out = False
    elif user_specified_brand and ms == MatchSource.KEYWORD and not branded_strong_keyword:
        needs_out = True

    return ResolvedProduct(
        product_name=winner.name,
        sku=use_sku if tier == ConfidenceLevel.HIGH else None,
        category=winner.category,
        image_url=image_url,
        brand=winner.brand if not user_specified_brand else None,
        size=winner.size,
        confidence=tier,
        confidence_numeric=conf_num,
        needs_specification=needs_out,
        api_suggestions=suggestions,
        match_source=ms,
        match_reason=_match_reason(winner, ms),
    )


def _title_case_safe(text: str) -> str:
    if not text:
        return text
    return " ".join(word.capitalize() for word in text.split())


async def maybe_llm_rerank_sku(
    normalized_item: NormalizedItem,
    suggestions: list[AutocompleteProduct],
) -> str | None:
    """Optionally return sku of LLM-chosen best candidate among top N."""
    settings = get_settings()
    if not settings.enable_llm_match_rerank or len(suggestions) < 2:
        return None
    n = max(2, min(settings.llm_rerank_top_n, len(suggestions)))
    top = suggestions[:n]
    try:
        from app.services.match_rerank_llm import pick_best_candidate_sku

        return await pick_best_candidate_sku(normalized_item, top)
    except Exception as e:
        print(f"LLM match rerank skipped: {e}")
        return None
