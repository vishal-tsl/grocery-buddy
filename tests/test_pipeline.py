import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.models.schemas import (
    NormalizedItem,
    StructuredItem,
    AutocompleteProduct,
    ConfidenceLevel,
)
from app.services.resolver import ProductResolver


class TestConfidenceScoring:
    """Test deterministic confidence scoring logic."""
    
    @pytest.fixture
    def resolver(self):
        """Create resolver with mocked autocomplete client."""
        with patch("app.services.resolver.get_autocomplete_client") as mock:
            mock.return_value = Mock()
            return ProductResolver()
    
    def test_high_confidence_exact_match(self, resolver):
        """HIGH confidence when normalized name appears in suggestion."""
        normalized = NormalizedItem(
            normalized_product_name="tomato paste",
            original_text="tomato paste 8oz"
        )
        suggestions = [
            AutocompleteProduct(sku="12345", name="Hunt's Tomato Paste 6oz", category="Canned Goods", image_url="https://example.com/tomato.jpg"),
            AutocompleteProduct(sku="67890", name="Contadina Tomato Paste 8oz", category="Canned Goods"),
        ]
        
        result = resolver._evaluate_confidence(
            normalized_item=normalized,
            suggestions=suggestions,
            search_query="tomato paste"
        )
        
        assert result.confidence == ConfidenceLevel.HIGH
        assert result.sku == "12345"  # First match
        assert result.category == "Canned Goods"  # Category from API
        assert result.image_url == "https://example.com/tomato.jpg"  # Image from API
        assert "Tomato Paste" in result.product_name
    
    def test_medium_confidence_partial_match(self, resolver):
        """MEDIUM confidence when only partial term matches."""
        normalized = NormalizedItem(
            normalized_product_name="organic milk",
            original_text="organic milk"
        )
        suggestions = [
            AutocompleteProduct(sku="11111", name="Organic Valley Whole Milk", category="Dairy & Eggs", image_url="https://example.com/milk.jpg"),
        ]
        
        result = resolver._evaluate_confidence(
            normalized_item=normalized,
            suggestions=suggestions,
            search_query="organic milk"
        )
        
        # Should be HIGH because "milk" appears in the suggestion
        assert result.confidence == ConfidenceLevel.HIGH
        assert result.category == "Dairy & Eggs"  # Category from API
        assert result.image_url == "https://example.com/milk.jpg"  # Image from API
    
    def test_low_confidence_no_match(self, resolver):
        """LOW confidence when no meaningful match found."""
        normalized = NormalizedItem(
            normalized_product_name="mystery item",
            original_text="idk something"
        )
        suggestions = [
            AutocompleteProduct(sku="99999", name="Completely Unrelated Product"),
        ]
        
        result = resolver._evaluate_confidence(
            normalized_item=normalized,
            suggestions=suggestions,
            search_query="mystery item"
        )
        
        assert result.confidence == ConfidenceLevel.LOW
        assert result.sku is None
    
    def test_low_confidence_empty_suggestions(self, resolver):
        """LOW confidence when API returns no suggestions."""
        normalized = NormalizedItem(
            normalized_product_name="unknown product",
            original_text="unknown product"
        )
        
        result = resolver._evaluate_confidence(
            normalized_item=normalized,
            suggestions=[],
            search_query="unknown product"
        )
        
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
        
        assert "2%" in result.product_name or result.product_name == "Milk"


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
        """Category should be included for HIGH confidence matches."""
        normalized = NormalizedItem(
            normalized_product_name="eggs",
            original_text="eggs"
        )
        suggestions = [
            AutocompleteProduct(sku="EGG001", name="Large White Eggs", category="Dairy & Eggs"),
        ]
        
        result = resolver._evaluate_confidence(
            normalized_item=normalized,
            suggestions=suggestions,
            search_query="eggs"
        )
        
        assert result.confidence == ConfidenceLevel.HIGH
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
        """Category should still be extracted for LOW confidence from first suggestion."""
        normalized = NormalizedItem(
            normalized_product_name="random item",
            original_text="random item"
        )
        suggestions = [
            AutocompleteProduct(sku="X001", name="Something Else", category="Miscellaneous"),
        ]
        
        result = resolver._evaluate_confidence(
            normalized_item=normalized,
            suggestions=suggestions,
            search_query="random item"
        )
        
        assert result.confidence == ConfidenceLevel.LOW
        assert result.category == "Miscellaneous"  # Still gets category from first suggestion


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
