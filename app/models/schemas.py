from pydantic import BaseModel, Field
from enum import Enum


class ItemIntent(str, Enum):
    """Classifier output: how specific the user's line is."""
    GENERIC = "generic"
    BRANDED = "branded"
    AMBIGUOUS = "ambiguous"


class ConfidenceLevel(str, Enum):
    """Confidence level for product resolution."""
    HIGH = "high"      # Exact or strong semantic match
    MEDIUM = "medium"  # Category-level or partial match
    LOW = "low"        # Weak or no meaningful match


class ParseListRequest(BaseModel):
    """Request body for POST /parse-list endpoint."""
    text: str = Field(..., description="Raw grocery text input (multi-line, messy)")


class NormalizedItem(BaseModel):
    """Intermediate representation after normalization (internal use)."""
    normalized_product_name: str
    quantity: float | None = None
    unit: str | None = None
    modifiers: list[str] = Field(default_factory=list)
    notes: str = ""
    original_text: str = ""
    has_brand: bool = False  # True if user specified a brand name
    # Full user paste or recipe block — used for context-aware re-ranking
    prompt_context: str | None = None
    # Optional LLM intent; resolver infers from has_brand if missing
    item_intent: ItemIntent | None = None


class ProductOption(BaseModel):
    """A product option from API suggestions."""
    sku: str
    name: str
    brand: str | None = None
    image_url: str | None = None


class MatchSource(str, Enum):
    """How the item was resolved: product key, keyword match, or plain AI text."""
    PRODUCT = "product"   # Fetched from backend using product key (SKU match)
    KEYWORD = "keyword"   # Fetched from backend using keyword/category match
    AI_TEXT = "ai_text"   # Plain AI-normalized text, no backend product match


class StructuredItem(BaseModel):
    """Final output item conforming to the strict output contract."""
    product_name: str
    sku: str | None = None
    quantity: float | None = None
    unit: str | None = None
    category: str | None = None  # Category from Autocomplete API
    image_url: str | None = None  # Image from Autocomplete API
    brand: str | None = None  # Brand from API
    size: str | None = None  # Size from API
    notes: str = ""
    needs_specification: bool = False  # True if user should choose from options
    options: list[ProductOption] = []  # Alternative product options
    match_source: MatchSource = MatchSource.AI_TEXT  # product | keyword | ai_text
    match_reason: str = ""  # Why mapped to product/keyword (visible in network response)
    confidence: float = 0.0  # numeric confidence score (e.g., 0.95)
    confidence_tier: ConfidenceLevel | None = None  # high / medium / low (optional for clients)
    selected_option_index: int | None = None  # 1-based index in options[] that was auto-selected, if any
    selected_suggestion_index: int | None = None  # 1-based index among full API suggestions (e.g. 3 of 20)
    total_suggestions: int | None = None  # total suggestions returned by API (e.g. 20)
    autocomplete_query: str = ""  # phrase/word sent to autocomplete to fetch this item


class ParseListResponse(BaseModel):
    """Response body for POST /parse-list endpoint."""
    items: list[StructuredItem]


class SuggestionType(str, Enum):
    """Autocomplete API suggestion type: product (specific SKU) or keyword (category/type)."""
    PRODUCT = "product"
    KEYWORD = "keyword"


class AutocompleteProduct(BaseModel):
    """Product suggestion from Autocomplete API."""
    sku: str  # Maps to 'id' from API (or composite for keywords)
    name: str  # Exact name from API (name / productName / typeName)
    brand: str | None = None
    category: str | None = None
    type_id: int | None = None
    type_name: str | None = None
    image_url: str | None = None
    size: str | None = None
    suggestion_type: SuggestionType = SuggestionType.PRODUCT  # product vs keyword from API


class ResolvedProduct(BaseModel):
    """Product after resolution with confidence scoring."""
    product_name: str
    sku: str | None = None
    category: str | None = None
    image_url: str | None = None
    brand: str | None = None
    size: str | None = None
    confidence: ConfidenceLevel
    needs_specification: bool = False
    api_suggestions: list[AutocompleteProduct] = Field(default_factory=list)
    match_source: MatchSource = MatchSource.AI_TEXT  # product | keyword | ai_text (must match match_reason)
    match_reason: str = ""
    # Calibrated numeric score in ~[0.35, 0.95] for UI; optional for backward compat
    confidence_numeric: float | None = None


# Recipe-related schemas
class RecipeRequest(BaseModel):
    """Request body for POST /recipe-to-list endpoint."""
    input: str = Field(..., description="Recipe name (e.g., 'Chicken Alfredo') or URL to recipe page")


class RecipeResponse(BaseModel):
    """Response body for POST /recipe-to-list endpoint."""
    recipe_name: str
    servings: int | None = None
    source: str  # "generated", "extracted", or "structured_data"
    source_url: str | None = None
    ingredients_raw: list[str]  # Original ingredient strings
    items: list[StructuredItem]  # Parsed and resolved items


# Agent APIs schemas
class AgentParseRequest(BaseModel):
    """Request body for POST /agents/parse endpoint."""
    text: str = Field(..., description="Raw grocery text input (multi-line, messy)")


class AgentParseResponse(BaseModel):
    """Response body for POST /agents/parse endpoint."""
    items: list[str]


class AgentNormalizeRequest(BaseModel):
    """Request body for POST /agents/normalize endpoint."""
    items: list[str] = Field(..., description="List of raw grocery item strings to normalize")


class AgentNormalizeResponse(BaseModel):
    """Response body for POST /agents/normalize endpoint."""
    items: list[NormalizedItem]


class AgentResolveRequest(BaseModel):
    """Request body for POST /agents/resolve endpoint."""
    items: list[NormalizedItem] = Field(..., description="List of normalized items to resolve against the product catalog")
    prompt_context: str | None = Field(
        default=None,
        description="Optional full user paste applied to items missing prompt_context",
    )


class AgentResolveResponse(BaseModel):
    """Response body for POST /agents/resolve endpoint."""
    items: list[StructuredItem]

