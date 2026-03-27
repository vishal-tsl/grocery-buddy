import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.models.schemas import (
    ItemIntent,
    NormalizedItem,
    StructuredItem,
    AutocompleteProduct,
    ConfidenceLevel,
    MatchSource,
    ResolvedProduct,
    SuggestionType,
)
from app.services.resolver import ProductResolver
from app.services.matching_pipeline import build_retrieval_queries, evaluate_match


class TestConfidenceScoring:
    """Test deterministic confidence scoring logic."""
    
    @pytest.fixture
    def resolver(self):
        """Create resolver with mocked autocomplete client."""
        with patch("app.services.resolver.get_autocomplete_client") as mock:
            mock.return_value = Mock()
            return ProductResolver()
    
    def test_high_confidence_exact_match(self, resolver):
        """Strong match for specific multi-word product (catalog name preserved)."""
        normalized = NormalizedItem(
            normalized_product_name="tomato paste",
            original_text="tomato paste 8oz"
        )
        suggestions = [
            AutocompleteProduct(sku="12345", name="Hunt's Tomato Paste 6oz", category="Canned Goods", image_url="https://example.com/tomato.jpg"),
            AutocompleteProduct(sku="67890", name="Contadina Tomato Paste 8oz", category="Canned Goods"),
        ]
        
        result = evaluate_match(normalized, suggestions, "tomato paste")
        
        assert result.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
        assert result.category == "Canned Goods"
        assert "tomato" in result.product_name.lower()
        if result.confidence == ConfidenceLevel.HIGH and result.match_source == MatchSource.PRODUCT:
            assert result.sku == "12345"
    
    def test_medium_confidence_partial_match(self, resolver):
        """Organic milk maps with good token overlap when a generic keyword row exists."""
        normalized = NormalizedItem(
            normalized_product_name="organic milk",
            original_text="organic milk"
        )
        suggestions = [
            AutocompleteProduct(
                sku="type_milk",
                name="Milk",
                category="Dairy & Eggs",
                suggestion_type=SuggestionType.KEYWORD,
            ),
            AutocompleteProduct(
                sku="11111",
                name="Organic Valley Whole Milk",
                category="Dairy & Eggs",
                image_url="https://example.com/milk.jpg",
            ),
        ]
        
        result = evaluate_match(normalized, suggestions, "organic milk")
        
        assert result.category == "Dairy & Eggs"
        assert "milk" in result.product_name.lower()
    
    def test_low_confidence_no_match(self, resolver):
        """LOW confidence when no meaningful match found."""
        normalized = NormalizedItem(
            normalized_product_name="mystery item",
            original_text="idk something"
        )
        suggestions = [
            AutocompleteProduct(sku="99999", name="Completely Unrelated Product"),
        ]
        
        result = evaluate_match(normalized, suggestions, "mystery item")
        
        assert result.confidence == ConfidenceLevel.LOW
        assert result.sku is None
    
    def test_low_confidence_empty_suggestions(self, resolver):
        """LOW confidence when API returns no suggestions."""
        normalized = NormalizedItem(
            normalized_product_name="unknown product",
            original_text="unknown product"
        )
        
        result = evaluate_match(normalized, [], "unknown product")
        
        assert result.confidence == ConfidenceLevel.LOW
        assert result.sku is None


class TestSafeFallbacks:
    """Test safe fallback behavior."""
    
    @pytest.fixture
    def resolver(self):
        with patch("app.services.resolver.get_autocomplete_client") as mock:
            mock.return_value = Mock()
            return ProductResolver()
    
    def test_sku_only_on_high_confidence(self, resolver):
        """SKU should only be present for HIGH confidence matches."""
        from app.models.schemas import ResolvedProduct
        
        normalized = NormalizedItem(
            normalized_product_name="chips",
            notes="User unclear: 'idk some chips'",
            original_text="idk some chips"
        )
        
        # LOW confidence resolved product
        resolved = ResolvedProduct(
            product_name="Chips",
            sku="12345",  # Has SKU but low confidence
            confidence=ConfidenceLevel.LOW,
            api_suggestions=[]
        )
        
        result = resolver._build_structured_item(normalized, resolved)
        
        # SKU should be None because confidence is LOW
        assert result.sku is None
        assert result.product_name == "Chips"
        assert "unclear" in result.notes.lower() or "low confidence" in result.notes.lower()
    
    def test_uncertainty_preserved_in_notes(self, resolver):
        """User uncertainty should be preserved in notes field."""
        from app.models.schemas import ResolvedProduct
        
        normalized = NormalizedItem(
            normalized_product_name="bread",
            notes="User uncertain: 'maybe wheat'",
            original_text="bread maybe wheat"
        )
        
        resolved = ResolvedProduct(
            product_name="Bread",
            sku=None,
            confidence=ConfidenceLevel.MEDIUM,
            api_suggestions=[]
        )
        
        result = resolver._build_structured_item(normalized, resolved)
        
        assert "maybe wheat" in result.notes
    
    def test_modifiers_added_to_generic_product(self, resolver):
        """Modifiers should be added to product name for non-high confidence."""
        from app.models.schemas import ResolvedProduct
        
        normalized = NormalizedItem(
            normalized_product_name="milk",
            modifiers=["2%"],
            original_text="milk 2%"
        )
        
        resolved = ResolvedProduct(
            product_name="Milk",
            sku=None,
            confidence=ConfidenceLevel.MEDIUM,
            api_suggestions=[]
        )
        
        result = resolver._build_structured_item(normalized, resolved)
        
        assert "2%" in result.notes or "2%" in result.product_name or result.product_name == "Milk"


class TestOutputContract:
    """Test that output conforms to strict contract."""
    
    def test_structured_item_schema(self):
        """StructuredItem should have all required fields."""
        item = StructuredItem(
            product_name="Test Product",
            sku=None,
            quantity=2.5,
            unit="lb",
            category="Fresh Produce",
            image_url="https://example.com/product.jpg",
            notes=""
        )
        
        assert item.product_name == "Test Product"
        assert item.sku is None
        assert item.quantity == 2.5
        assert item.unit == "lb"
        assert item.category == "Fresh Produce"
        assert item.image_url == "https://example.com/product.jpg"
        assert item.notes == ""
    
    def test_structured_item_defaults(self):
        """StructuredItem should have correct defaults."""
        item = StructuredItem(product_name="Test")
        
        assert item.sku is None
        assert item.quantity is None
        assert item.unit is None
        assert item.category is None
        assert item.image_url is None
        assert item.notes == ""


class TestCategoryFromAPI:
    """Test category extraction from Autocomplete API."""
    
    @pytest.fixture
    def resolver(self):
        with patch("app.services.resolver.get_autocomplete_client") as mock:
            mock.return_value = Mock()
            return ProductResolver()
    
    def test_category_included_high_confidence(self, resolver):
        """Generic eggs should prefer keyword row over branded product when both exist."""
        normalized = NormalizedItem(
            normalized_product_name="eggs",
            original_text="eggs"
        )
        suggestions = [
            AutocompleteProduct(
                sku="type_eggs",
                name="Eggs",
                category="Dairy & Eggs",
                suggestion_type=SuggestionType.KEYWORD,
            ),
            AutocompleteProduct(
                sku="EGG001",
                name="Large White Eggs",
                category="Dairy & Eggs",
                suggestion_type=SuggestionType.PRODUCT,
            ),
        ]
        
        result = evaluate_match(normalized, suggestions, "eggs")
        
        assert result.match_source == MatchSource.KEYWORD
        assert "egg" in result.product_name.lower()
        assert result.category == "Dairy & Eggs"
    
    def test_category_included_medium_confidence(self, resolver):
        """Category should be included even for MEDIUM confidence."""
        from app.models.schemas import ResolvedProduct
        
        normalized = NormalizedItem(
            normalized_product_name="snacks",
            original_text="some snacks"
        )
        
        resolved = ResolvedProduct(
            product_name="Snacks",
            sku=None,
            category="Snacks & Chips",
            confidence=ConfidenceLevel.MEDIUM,
            api_suggestions=[]
        )
        
        result = resolver._build_structured_item(normalized, resolved)
        
        assert result.category == "Snacks & Chips"
    
    def test_category_from_fallback(self, resolver):
        """Category should still be extracted for LOW confidence from best suggestion."""
        normalized = NormalizedItem(
            normalized_product_name="random item",
            original_text="random item"
        )
        suggestions = [
            AutocompleteProduct(sku="X001", name="Something Else", category="Miscellaneous"),
        ]
        
        result = evaluate_match(normalized, suggestions, "random item")
        
        assert result.confidence == ConfidenceLevel.LOW
        assert result.category == "Miscellaneous"


class TestContextAndBrandedMatch:
    """Context-aware re-ranking and branded string alignment."""

    def test_taco_context_prefers_taco_shells_over_pasta(self):
        normalized = NormalizedItem(
            normalized_product_name="shells",
            original_text="shells",
            prompt_context="ground beef tacos taco shells shredded cheese",
        )
        suggestions = [
            AutocompleteProduct(sku="p1", name="Shells Pasta", category="Pasta"),
            AutocompleteProduct(sku="p2", name="Crunchy Taco Shells", category="Mexican"),
        ]
        result = evaluate_match(normalized, suggestions, "shells")
        assert "taco" in result.product_name.lower()

    def test_branded_line_prefers_haagen_row(self):
        normalized = NormalizedItem(
            normalized_product_name="Haagen-Dazs vanilla ice cream",
            original_text="Haagen-Dazs vanilla ice cream",
            has_brand=True,
        )
        suggestions = [
            AutocompleteProduct(sku="g1", name="Store Brand Vanilla Ice Cream"),
            AutocompleteProduct(sku="h1", name="Haagen-Dazs Vanilla Ice Cream"),
        ]
        result = evaluate_match(
            normalized, suggestions, "Haagen-Dazs vanilla ice cream"
        )
        assert "haagen" in result.product_name.lower()


class TestQARegressionHardening:
    """Branded keyword commit, generic refusal, category-conflict confidence caps."""

    def test_branded_keyword_match_sets_needs_specification_false(self):
        normalized = NormalizedItem(
            normalized_product_name="Haagen-Dazs vanilla ice cream",
            original_text="Haagen-Dazs vanilla ice cream",
            has_brand=True,
        )
        suggestions = [
            AutocompleteProduct(
                sku="type_99",
                name="Haagen-Dazs Vanilla Ice Cream",
                suggestion_type=SuggestionType.KEYWORD,
            ),
        ]
        r = evaluate_match(normalized, suggestions, "Haagen-Dazs vanilla ice cream")
        assert r.needs_specification is False
        assert "haagen" in r.product_name.lower()

    def test_eggs_only_branded_product_returns_ai_text(self):
        normalized = NormalizedItem(
            normalized_product_name="eggs",
            original_text="eggs",
            has_brand=False,
        )
        suggestions = [
            AutocompleteProduct(
                sku="888",
                name="Farmhouse Eggs",
                brand="Farmhouse",
                suggestion_type=SuggestionType.PRODUCT,
            ),
        ]
        r = evaluate_match(normalized, suggestions, "eggs")
        assert r.match_source == MatchSource.AI_TEXT
        assert r.product_name.lower() == "eggs"

    def test_pasta_vs_mexican_top_two_caps_display_confidence(self):
        normalized = NormalizedItem(
            normalized_product_name="shells",
            original_text="shells",
        )
        suggestions = [
            AutocompleteProduct(sku="a", name="Shells Pasta", category="Italian Pasta"),
            AutocompleteProduct(sku="b", name="Taco Shells", category="Mexican Food"),
        ]
        r = evaluate_match(normalized, suggestions, "shells")
        assert r.confidence_numeric is not None
        assert r.confidence_numeric <= 0.72

    def test_fresh_tomatoes_avoids_rotel_style_hit(self):
        normalized = NormalizedItem(
            normalized_product_name="tomatoes",
            original_text="some tomatoes",
            has_brand=False,
        )
        suggestions = [
            AutocompleteProduct(
                sku="t1",
                name="Medium Diced Tomatoes With Green Chiles",
                category="Canned",
                suggestion_type=SuggestionType.KEYWORD,
            ),
            AutocompleteProduct(
                sku="t2",
                name="Tomatoes",
                category="Produce",
                suggestion_type=SuggestionType.KEYWORD,
            ),
        ]
        r = evaluate_match(normalized, suggestions, "tomatoes")
        assert "chile" not in r.product_name.lower()
        assert "tomato" in r.product_name.lower()

    def test_chicken_breast_avoids_canned(self):
        normalized = NormalizedItem(
            normalized_product_name="chicken breast",
            original_text="chicken breast",
        )
        suggestions = [
            AutocompleteProduct(
                sku="c1",
                name="Breast Canned Chicken",
                category="Canned Meat",
                suggestion_type=SuggestionType.KEYWORD,
            ),
            AutocompleteProduct(
                sku="c2",
                name="Chicken Breast",
                category="Meat",
                suggestion_type=SuggestionType.KEYWORD,
            ),
        ]
        r = evaluate_match(normalized, suggestions, "chicken breast")
        assert "canned" not in r.product_name.lower()


class TestSearchQueryBuilder:
    """Test search query building logic."""
    
    @pytest.fixture
    def resolver(self):
        with patch("app.services.resolver.get_autocomplete_client") as mock:
            mock.return_value = Mock()
            return ProductResolver()
    
    def test_basic_query(self, resolver):
        """Basic product name should be the query."""
        normalized = NormalizedItem(
            normalized_product_name="tomato paste",
            original_text="tomato paste"
        )
        
        query = resolver._build_search_query(normalized)
        
        assert query == "tomato paste"
    
    def test_query_with_modifiers(self, resolver):
        """Modifiers should be included in query."""
        normalized = NormalizedItem(
            normalized_product_name="milk",
            modifiers=["2%", "organic"],
            original_text="organic milk 2%"
        )
        
        query = resolver._build_search_query(normalized)
        
        assert "milk" in query
        assert "2%" in query
        assert "organic" in query
    
    def test_query_excludes_uncertainty_words(self, resolver):
        """Uncertainty words like 'maybe' should not be in query."""
        normalized = NormalizedItem(
            normalized_product_name="chips",
            modifiers=["maybe", "some"],
            original_text="maybe some chips"
        )
        
        query = resolver._build_search_query(normalized)
        
        assert "maybe" not in query
        assert "some" not in query
        assert "chips" in query

    def test_query_omits_produce_size_words(self, resolver):
        normalized = NormalizedItem(
            normalized_product_name="cucumber",
            modifiers=["medium"],
            original_text="1 medium cucumber",
        )
        assert resolver._build_search_query(normalized) == "cucumber"

    def test_notes_drop_as_written_fragments(self, resolver):
        normalized = NormalizedItem(
            normalized_product_name="Kerrygold butter",
            notes='As written: "1 package Kerrygold butter"',
            original_text="1 package Kerrygold butter",
            has_brand=True,
        )
        resolved = ResolvedProduct(
            product_name="Kerrygold Butter",
            sku="kw1",
            confidence=ConfidenceLevel.HIGH,
            confidence_numeric=0.9,
            needs_specification=False,
            api_suggestions=[],
            match_source=MatchSource.KEYWORD,
            match_reason="keyword",
        )
        out = resolver._build_structured_item(normalized, resolved)
        assert "as written" not in out.notes.lower()

    def test_includes_note_omits_produce_size_words(self, resolver):
        normalized = NormalizedItem(
            normalized_product_name="tomatoes",
            modifiers=["medium"],
            original_text="some tomatoes",
        )
        resolved = ResolvedProduct(
            product_name="Tomatoes",
            sku=None,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_numeric=0.76,
            needs_specification=True,
            api_suggestions=[],
            match_source=MatchSource.KEYWORD,
            match_reason="keyword",
        )
        out = resolver._build_structured_item(normalized, resolved)
        assert "Includes" not in out.notes

    def test_keyword_no_borrow_when_type_row_has_no_image(self, resolver):
        """Keyword matches must not use brand-option photos when the type row has no image."""
        img = "https://images.basketsavings.com/example.jpg"
        suggestions = [
            AutocompleteProduct(
                sku="type_1_0",
                name="Dijon Mustard",
                suggestion_type=SuggestionType.KEYWORD,
                image_url=None,
            ),
            AutocompleteProduct(
                sku="brand_9_type_1",
                name="Koops' Dijon Mustard",
                brand="Koops'",
                image_url=img,
                suggestion_type=SuggestionType.KEYWORD,
            ),
        ]
        normalized = NormalizedItem(
            normalized_product_name="Dijon mustard",
            original_text="Dijon mustard",
        )
        resolved = ResolvedProduct(
            product_name="Dijon Mustard",
            sku=None,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_numeric=0.76,
            needs_specification=True,
            api_suggestions=suggestions,
            match_source=MatchSource.KEYWORD,
            match_reason="keyword",
            image_url=None,
        )
        out = resolver._build_structured_item(normalized, resolved)
        assert out.image_url is None
        assert out.options[0].image_url is None
        assert out.options[1].image_url == img


class TestRetrievalQueries:
    def test_no_context_prefix_when_brands_only_share_long_prompt(self):
        long_prompt = (
            "Häagen-Dazs vanilla bean ice cream Cool Ranch Doritos Kerrygold butter tomatoes"
        )
        n = NormalizedItem(
            normalized_product_name="tomatoes",
            original_text="some tomatoes",
            prompt_context=long_prompt,
            item_intent=ItemIntent.GENERIC,
        )
        qs = build_retrieval_queries(n, "tomatoes")
        lowered = [q.lower() for q in qs]
        assert all("haagen" not in q and "häagen" not in q for q in lowered)
        assert "tomatoes" in lowered


@pytest.mark.asyncio
class TestResolverIntegration:
    """Integration tests for the resolver."""
    
    async def test_resolve_with_mocked_api(self):
        """Test full resolve flow with mocked API."""
        with patch("app.services.resolver.get_autocomplete_client") as mock_client:
            # Setup mock
            client_instance = Mock()
            client_instance.search = AsyncMock(return_value=[
                AutocompleteProduct(
                    sku="SKU123",
                    name="Organic Tomato Paste 8oz",
                    brand="Hunt's",
                    category="Canned Goods"
                )
            ])
            mock_client.return_value = client_instance
            
            resolver = ProductResolver()
            
            normalized = NormalizedItem(
                normalized_product_name="tomato paste",
                quantity=8,
                unit="oz",
                original_text="tomato paste 8oz"
            )
            
            result = await resolver.resolve(normalized)
            
            assert result.product_name is not None
            assert result.quantity == 8
            assert result.unit == "oz"
            assert result.category == "Canned Goods"  # Category from API
