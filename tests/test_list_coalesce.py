from app.models.schemas import MatchSource, StructuredItem
from app.services.list_coalesce import merge_duplicate_structured_items


def test_merge_duplicate_rows_sums_quantity():
    a = StructuredItem(
        product_name="La Fermière Mango Yogurt",
        sku="type_42",
        quantity=1.0,
        match_source=MatchSource.KEYWORD,
        confidence=0.82,
        notes="foo",
    )
    b = StructuredItem(
        product_name="La Fermière Mango Yogurt",
        sku="type_42",
        quantity=1.0,
        match_source=MatchSource.KEYWORD,
        confidence=0.75,
        notes="foo",
    )
    out = merge_duplicate_structured_items([a, b])
    assert len(out) == 1
    assert out[0].quantity == 1.0
    assert out[0].confidence == 0.82
    assert out[0].notes == "foo"


def test_merge_treats_missing_quantity_as_one():
    a = StructuredItem(product_name="Eggs", sku="sku1", match_source=MatchSource.PRODUCT)
    b = StructuredItem(product_name="Eggs", sku="sku1", quantity=2.0, match_source=MatchSource.PRODUCT)
    out = merge_duplicate_structured_items([a, b])
    assert len(out) == 1
    assert out[0].quantity == 3.0


def test_unstable_type_sku_index_still_merges():
    """Autocomplete uses type_{typeId}_{idx}; idx must not block duplicate-line merge."""
    a = StructuredItem(
        product_name="La Fermière Mango Yogurt",
        sku="type_99_0",
        quantity=1.0,
        match_source=MatchSource.KEYWORD,
        confidence=0.82,
    )
    b = StructuredItem(
        product_name="La Fermière Mango Yogurt",
        sku="type_99_3",
        quantity=1.0,
        match_source=MatchSource.KEYWORD,
        confidence=0.82,
    )
    out = merge_duplicate_structured_items([a, b])
    assert len(out) == 1
    assert out[0].quantity == 1.0


def test_keyword_merge_ignores_different_type_skus_same_product():
    a = StructuredItem(
        product_name="Haagen-Dazs Vanilla Bean Ice Cream",
        sku="type_100_0",
        quantity=None,
        match_source=MatchSource.KEYWORD,
        confidence=0.76,
    )
    b = StructuredItem(
        product_name="Häagen-Dazs Vanilla Bean Ice Cream",
        sku="type_200_3",
        quantity=None,
        match_source=MatchSource.KEYWORD,
        confidence=0.76,
    )
    out = merge_duplicate_structured_items([a, b])
    assert len(out) == 1


def test_chicken_breast_plural_singular_merge():
    a = StructuredItem(
        product_name="Chicken Breasts",
        sku="type_1_0",
        quantity=None,
        match_source=MatchSource.KEYWORD,
    )
    b = StructuredItem(
        product_name="Chicken Breast",
        sku="type_2_0",
        quantity=None,
        match_source=MatchSource.KEYWORD,
    )
    out = merge_duplicate_structured_items([a, b])
    assert len(out) == 1


def test_different_match_source_not_merged():
    a = StructuredItem(product_name="Milk", sku="x", match_source=MatchSource.KEYWORD)
    b = StructuredItem(product_name="Milk", sku="x", match_source=MatchSource.PRODUCT)
    out = merge_duplicate_structured_items([a, b])
    assert len(out) == 2
