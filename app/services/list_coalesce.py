"""Merge duplicate structured list lines (same catalog resolution) into one row with summed quantity."""

from __future__ import annotations

import re
import unicodedata

from app.models.schemas import MatchSource, StructuredItem

# Keyword rows from autocomplete use type_{typeId}_{listIndex}; index differs per fetch/merge.
_TYPE_SKU_WITH_IDX = re.compile(r"^type_(\d+)_\d+$")


def _fold_display_name(name: str) -> str:
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.split()).lower()


def _canonical_identity_sku(sku: str) -> str:
    """Stable key for merged API rows so duplicate lines coalesce."""
    sku = (sku or "").strip()
    m = _TYPE_SKU_WITH_IDX.match(sku)
    if m:
        return f"type_{m.group(1)}"
    return sku


def _canonical_keyword_merge_name(name: str) -> str:
    """
    Fold + light normalization so catalog duplicates merge (plural/singular, wording).
    """
    f = _fold_display_name(name)
    f = re.sub(r"\bchicken breasts\b", "chicken breast", f)
    f = re.sub(r"\btomatoes\b", "tomato", f)
    f = re.sub(r"\bavocados\b", "avocado", f)
    f = re.sub(r"\bbella mushrooms\b", "bella mushroom", f)
    f = re.sub(r"\bportobello mushrooms?\b", "portobello mushroom", f)
    return f


def _qty_weight(q: float | None) -> float:
    """Treat missing quantity as 1 when stacking rows with different explicit counts."""
    return 1.0 if q is None else float(q)


def _combine_merged_quantity(q_a: float | None, q_b: float | None) -> float | None:
    """
    Merge quantities for the same resolved row.
    - Both null → null (UI default 1; avoids double-counting speech duplicates).
    - Same non-null number → keep one copy (duplicate parser rows).
    - One null → sum with implicit 1 for the missing side (mixed explicit runs).
    - Different positive numbers → add.
    """
    if q_a is None and q_b is None:
        return None
    if q_a is None or q_b is None:
        return _qty_weight(q_a) + _qty_weight(q_b)
    fa, fb = float(q_a), float(q_b)
    if fa == fb:
        return fa
    return fa + fb


def _match_source_key(ms: MatchSource | str) -> str:
    if isinstance(ms, MatchSource):
        return ms.value
    return str(ms).lower().split(".")[-1]


def _merge_notes(a: str, b: str) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for block in (a, b):
        for p in block.split(" | "):
            t = p.strip()
            if not t:
                continue
            k = t.lower()
            if k not in seen:
                seen.add(k)
                parts.append(t)
    return " | ".join(parts)


def merge_duplicate_structured_items(items: list[StructuredItem]) -> list[StructuredItem]:
    """
    Combine rows that resolved to the same product identity.
    Keyword rows merge on normalized display name (API type_* ids often differ for the same hit).
    Quantities merge with duplicate-aware rules; notes de-dupe; confidence max.
    """
    groups: dict[tuple, StructuredItem] = {}
    order: list[tuple] = []

    for item in items:
        ms_key = _match_source_key(item.match_source)
        sku_raw = (item.sku or "").strip()
        name_fold = _fold_display_name(item.product_name)

        if ms_key == MatchSource.KEYWORD.value:
            key = (ms_key, _canonical_keyword_merge_name(item.product_name))
        else:
            id_sku = (
                _canonical_identity_sku(sku_raw)
                if sku_raw.startswith("type_")
                else sku_raw
            )
            key = (ms_key, name_fold, id_sku)

        if key not in groups:
            groups[key] = item.model_copy(deep=True)
            order.append(key)
            continue

        cur = groups[key]
        q_new = _combine_merged_quantity(cur.quantity, item.quantity)
        notes_m = _merge_notes(cur.notes, item.notes)
        conf = max(cur.confidence, item.confidence)
        groups[key] = cur.model_copy(
            update={
                "quantity": q_new,
                "unit": cur.unit or item.unit,
                "notes": notes_m,
                "confidence": conf,
                "needs_specification": cur.needs_specification or item.needs_specification,
                "image_url": cur.image_url or item.image_url,
                "category": cur.category or item.category,
                "brand": cur.brand or item.brand,
            }
        )

    return [groups[k] for k in order]
