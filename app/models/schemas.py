from pydantic import BaseModel, Field
from enum import Enum


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


class ProductOption(BaseModel):
    """A product option from API suggestions."""
    sku: str
    name: str
    brand: str | None = None
    image_url: str | None = None


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


class ParseListResponse(BaseModel):
    """Response body for POST /parse-list endpoint."""
    items: list[StructuredItem]


class AutocompleteProduct(BaseModel):
    """Product suggestion from Autocomplete API."""
    sku: str  # Maps to 'id' from API
    name: str
    brand: str | None = None
    category: str | None = None
    type_id: int | None = None
    type_name: str | None = None
    image_url: str | None = None
    size: str | None = None


class ResolvedProduct(BaseModel):
    """Product after resolution with confidence scoring."""
    product_name: str
    sku: str | None = None
    category: str | None = None  # Category from API
    image_url: str | None = None  # Image from API
    brand: str | None = None  # Brand from API
    size: str | None = None  # Size from API
    confidence: ConfidenceLevel
    needs_specification: bool = False  # True if multiple good matches
    api_suggestions: list[AutocompleteProduct] = Field(default_factory=list)
