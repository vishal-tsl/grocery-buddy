from app.agents.normalizer import (
    _line_has_item_count_evidence,
    _modifiers_only_if_on_line,
    _sanitize_quantity,
)


def test_too_is_not_quantity_two():
    assert _sanitize_quantity("avocados too", 2) is None
    assert _sanitize_quantity("avocados too", 2.0) is None
    assert _sanitize_quantity("2 avocados too", 2) == 2.0
    assert _sanitize_quantity("two avocados too", 2) == 2.0


def test_strict_no_invented_counts_without_numeral_or_word():
    assert _sanitize_quantity("some eggs", 12) is None
    assert _sanitize_quantity("some eggs", 1) is None
    assert _sanitize_quantity("eggs", 12) is None
    assert _sanitize_quantity("chicken breast", 2) is None
    assert _sanitize_quantity("portobello mushroom", 8) is None
    assert _sanitize_quantity("dozen eggs", 12) == 12.0
    assert _sanitize_quantity("12 eggs", 12) == 12.0


def test_quantity_ge_two_requires_evidence_on_line():
    assert _sanitize_quantity("some tomatoes", 3) is None
    assert _sanitize_quantity("3 tomatoes", 3) == 3.0
    assert _sanitize_quantity("three tomatoes", 3) == 3.0


def test_single_unit_count_kept_when_digit_on_line():
    assert _sanitize_quantity("1 medium cucumber", 1) == 1.0
    assert _sanitize_quantity("2 La Fermière mango yogurt", 2) == 2.0


def test_line_count_evidence():
    assert _line_has_item_count_evidence("some eggs") is False
    assert _line_has_item_count_evidence("dozen eggs") is True
    assert _line_has_item_count_evidence("milk 2%") is False
    assert _line_has_item_count_evidence("12 eggs") is True
    assert _line_has_item_count_evidence("3 tomatoes") is True
    monologue = (
        "Okay, let's make a list and add 2 La Fermière yogurt and some eggs, thanks"
    )
    assert _line_has_item_count_evidence(monologue) is False


def test_long_line_only_leading_count_counts():
    assert _line_has_item_count_evidence("x" * 120) is False
    assert _line_has_item_count_evidence("  3 " + "x" * 120) is True


def test_mid_line_add_two_not_evidence_on_longish_clause():
    """Parser sometimes keeps a clause; 'add 2 La …' must not prove count for 'eggs'."""
    clause = "Okay, let's make a list and add 2 La Fermière yogurt and some eggs, thanks"
    assert len(clause) > 48
    assert _line_has_item_count_evidence(clause) is False

def test_measure_unit_bypasses_count_guard():
    assert _sanitize_quantity("tomato paste 8oz", 8.0, unit="oz") == 8.0


def test_plural_product_name_not_treated_as_count_with_stray_digit():
    """'tomatoes' + qty 3 but no literal 3 — strip even if another digit exists in a long clause."""
    clause = "add 2 La Fermière yogurt and some tomatoes thanks"
    assert len(clause) > 48
    assert _sanitize_quantity(clause, 3.0, product_name="tomatoes") is None


def test_plural_line_keeps_quantity_when_digit_matches():
    assert _sanitize_quantity("3 tomatoes", 3.0, product_name="tomatoes") == 3.0


def test_chicken_breasts_qty_two_stripped_when_no_literal_two():
    assert (
        _sanitize_quantity(
            "then chicken breasts for dinner", 2.0, product_name="chicken breasts"
        )
        is None
    )


def test_size_modifiers_stripped_when_not_on_line():
    assert _modifiers_only_if_on_line(["medium"], "some tomatoes") == []
    assert _modifiers_only_if_on_line(["medium"], "1 medium cucumber") == ["medium"]
    assert _modifiers_only_if_on_line(["organic", "medium"], "organic milk") == ["organic"]
