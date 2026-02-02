# SLAI - Smart List AI Documentation

## Complete Technical Documentation

**Version:** 1.0.0  
**Last Updated:** February 2, 2026

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Folder Structure](#folder-structure)
4. [Backend (FastAPI)](#backend-fastapi)
   - [Configuration](#configuration)
   - [API Routes](#api-routes)
   - [LLM Agents](#llm-agents)
   - [Services](#services)
   - [Models & Schemas](#models--schemas)
5. [Frontend (Next.js)](#frontend-nextjs)
   - [Pages](#pages)
   - [Components](#components)
   - [API Client](#api-client)
   - [Styling](#styling)
6. [API Reference](#api-reference)
7. [Performance Optimizations](#performance-optimizations)
8. [Testing](#testing)
9. [Environment Setup](#environment-setup)

---

## Project Overview

SLAI (Smart List AI) is an AI-powered grocery list structuring engine that converts unstructured text input into clean, structured shopping lists. The system uses Google's Gemini LLM for natural language understanding and the BasketSavings Autocomplete API for product resolution.

### Key Features

- **Natural Language Parsing**: Understands messy input like "2 lb ground beef", "org milk", "salt butter"
- **Typo Correction**: Fixes common misspellings ("butr" → "Butter", "tomatoe" → "Tomato")
- **Quantity Extraction**: Parses quantities and units ("8oz", "2 lb", "half gallon", "dozen")
- **Brand Detection**: Identifies when users specify brands vs generic products
- **Product Resolution**: Matches input to real products via Autocomplete API
- **Brand Selection UI**: Prompts users to select specific brands when not specified
- **Confidence Scoring**: Applies guardrails to prevent hallucinated products

### Core Principles

| Principle | Description |
|-----------|-------------|
| **LLMs reason about language** | Gemini handles parsing, typo correction, normalization |
| **APIs decide on products** | Autocomplete API is the ONLY source of truth for products |
| **Code enforces correctness** | Deterministic confidence scoring and validation |
| **No hallucinations** | Never invent SKUs or product names not from API |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│         "butter, eggs, mlk 2%, tomatoe paste 8oz"               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Parse & Normalize (Single LLM Call)          │   │
│  │  • Splits input into items                                │   │
│  │  • Fixes typos: "mlk" → "milk", "tomatoe" → "tomato"     │   │
│  │  • Extracts quantities: "8oz" → quantity=8, unit="oz"    │   │
│  │  • Detects brands: "kerrygold butter" → has_brand=true   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Autocomplete API (Parallel Calls)               │   │
│  │  • Search each normalized product                         │   │
│  │  • Get SKUs, categories, images, brands                   │   │
│  │  • Returns top suggestions for each item                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Product Resolver (Deterministic)             │   │
│  │  • Confidence scoring (HIGH/MEDIUM/LOW)                   │   │
│  │  • Set needs_specification if no brand specified          │   │
│  │  • Build product options for brand selection              │   │
│  │  • Safe fallbacks for unmatched items                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STRUCTURED OUTPUT                             │
│  [                                                               │
│    { product_name: "Butter", needs_specification: true, ... },  │
│    { product_name: "Farmhouse Eggs", sku: "123", ... },         │
│    { product_name: "2% Reduced Fat Milk", ... },                │
│    { product_name: "Tomato Paste", quantity: 8, unit: "oz" }    │
│  ]                                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND                              │
│  • Quick Add Sheet for input                                     │
│  • Grocery list grouped by category                              │
│  • Brand Selection Sheet for specification                       │
│  • Item detail editing                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
slai/
├── app/                          # Backend (FastAPI)
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── config.py                 # Environment configuration (Pydantic Settings)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py             # API endpoints + LLM parsing logic
│   │   └── image_proxy.py        # Image proxy endpoint (unused)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── parser.py             # Gemini parser agent (legacy, now in routes.py)
│   │   └── normalizer.py         # Gemini normalizer agent (legacy, now in routes.py)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── autocomplete.py       # BasketSavings Autocomplete API client
│   │   ├── resolver.py           # Product resolution + confidence scoring
│   │   └── image_service.py      # OpenFoodFacts image fetcher
│   └── models/
│       ├── __init__.py
│       └── schemas.py            # Pydantic models for all data structures
│
├── frontend/                     # Frontend (Next.js)
│   ├── package.json              # Dependencies
│   ├── next.config.js            # Next.js configuration
│   ├── tailwind.config.ts        # Tailwind CSS configuration
│   ├── postcss.config.js         # PostCSS configuration
│   ├── tsconfig.json             # TypeScript configuration
│   └── src/
│       ├── app/                  # Next.js App Router pages
│       │   ├── layout.tsx        # Root layout with fonts
│       │   ├── globals.css       # Global styles + Tailwind
│       │   ├── page.tsx          # Home page (dashboard)
│       │   └── list/
│       │       ├── new/
│       │       │   └── page.tsx  # New list creation page
│       │       └── [id]/
│       │           └── page.tsx  # Existing list detail page
│       ├── components/           # Reusable UI components
│       │   ├── Icon.tsx          # Material Icons wrapper
│       │   ├── StatusBar.tsx     # Mobile status bar
│       │   ├── ListCard.tsx      # List card for dashboard
│       │   ├── GroceryItem.tsx   # Individual grocery item
│       │   ├── CategorySection.tsx  # Category grouping
│       │   ├── QuickAddSheet.tsx    # Bottom sheet for adding items
│       │   ├── ItemSpecSheet.tsx    # Item specification sheet
│       │   ├── BrandSelectSheet.tsx # Brand selection sheet
│       │   └── BottomToolbar.tsx    # Bottom toolbar
│       ├── lib/
│       │   └── api.ts            # Backend API client
│       └── types/
│           └── index.ts          # TypeScript interfaces
│
├── tests/                        # Test suite
│   ├── __init__.py
│   └── test_pipeline.py          # Unit and integration tests
│
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest configuration
├── .gitignore                    # Git ignore rules
├── README.md                     # Quick start guide
└── DOCUMENTATION.md              # This file
```

---

## Backend (FastAPI)

### Configuration

**File:** `app/config.py`

Uses Pydantic Settings for environment variable management with validation.

```python
class Settings(BaseSettings):
    # Gemini LLM
    gemini_api_key: str              # Google Gemini API key
    
    # Autocomplete API
    autocomplete_base_url: str       # API base URL
    autocomplete_auth_token: str     # Authorization token
    autocomplete_lat: float          # Latitude for location
    autocomplete_lng: float          # Longitude for location
    autocomplete_app_name: str       # App identifier
    autocomplete_app_version: str    # App version
    autocomplete_limit: int          # Max results per query
    autocomplete_include_images: bool
    autocomplete_exclude_subcategory: bool
    autocomplete_exclude_brand: bool # Set to False to include brands
```

**Environment Variables Required:**

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `AUTOCOMPLETE_AUTH_TOKEN` | BasketSavings auth token | `adc3d491...` |
| `AUTOCOMPLETE_LAT` | Store latitude | `44.8828` |
| `AUTOCOMPLETE_LNG` | Store longitude | `-93.2007` |

---

### API Routes

**File:** `app/api/routes.py`

#### POST `/api/v1/parse-list`

Main endpoint that orchestrates the entire pipeline.

**Request Body:**
```json
{
  "text": "butter, eggs, mlk 2%, tomatoe paste 8oz"
}
```

**Response:**
```json
{
  "items": [
    {
      "product_name": "Butter",
      "sku": null,
      "quantity": null,
      "unit": null,
      "category": "Dairy",
      "image_url": "https://images.basketsavings.com/...",
      "brand": null,
      "size": null,
      "notes": "",
      "needs_specification": true,
      "options": [
        { "sku": "123", "name": "Kerrygold Butter", "brand": "Kerrygold", "image_url": "..." },
        { "sku": "456", "name": "Land O'Lakes Butter", "brand": "Land O'Lakes", "image_url": "..." }
      ]
    }
  ]
}
```

**Pipeline Steps:**

1. **Parse & Normalize (Single LLM Call)**
   - Uses Gemini `gemini-2.0-flash` model
   - Minimal prompt for speed
   - Fixes typos, extracts quantities, detects brands

2. **Product Resolution (Parallel API Calls)**
   - All Autocomplete API calls run in parallel
   - Builds structured items with confidence scoring
   - Populates brand options for specification

#### GET `/health`

Health check endpoint.

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

### LLM Agents

**Files:** `app/agents/parser.py`, `app/agents/normalizer.py`

> **Note:** These are legacy files. The current implementation combines parsing and normalization into a single LLM call in `routes.py` for better performance.

The combined prompt in `routes.py`:

```python
COMBINED_PROMPT = """Parse grocery items. Fix typos. Return JSON array.

Format: [{"n":"product","q":null,"u":null,"m":[],"b":false}]
- n: product name (lowercase, fix typos: "salt butter"→"salted butter")
- q: quantity (number or null)
- u: unit (oz/lb/gallon or null)
- m: modifiers ["organic","2%","salted"]
- b: true if brand mentioned (Kerrygold, Fairlife)
"""
```

**Typo Corrections Handled:**

| Input | Output |
|-------|--------|
| `butr` | butter |
| `mlk` | milk |
| `tomatoe` | tomato |
| `cofee` | coffee |
| `chiken` | chicken |
| `ognion` | onion |
| `garlc` | garlic |
| `bred` | bread |
| `salt butter` | salted butter |
| `org milk` | organic milk |
| `xtra virgin` | extra virgin |

---

### Services

#### Autocomplete Client

**File:** `app/services/autocomplete.py`

Client for the BasketSavings Autocomplete API.

```python
class AutocompleteClient:
    async def search(self, query: str) -> list[AutocompleteProduct]:
        """
        Search for products via Autocomplete API.
        
        API Endpoint: GET /search2/search/suggested2
        
        Query Parameters:
        - query: Search term
        - limit: Max results (default: 20)
        - includeProducts: Include product SKUs
        - includeImages: Include product images
        - excludeSubcategory: Exclude subcategories
        - exludeBrand: Exclude brand suggestions (set False to include)
        - semanticEnabled: Enable vector search
        - enrichKeyword: Include keyword details
        
        Headers:
        - Authorization: Auth token
        - appName: App identifier
        - appVersion: App version
        - latitude: Store latitude
        - longitude: Store longitude
        """
```

**Response Parsing:**

The API returns various product types. The client extracts:

| Field | Source |
|-------|--------|
| `sku` | `id`, `sku`, or `productId` |
| `name` | `name`, `productName`, or `typeName` |
| `category` | `category`, `categoryName`, `aisle`, `department` |
| `brand` | `brandName` or `brand` |
| `image_url` | `imageUrl` (prefixed with base URL if relative) |
| `size` | `size` |

---

#### Product Resolver

**File:** `app/services/resolver.py`

Deterministic product resolution with confidence scoring.

```python
class ProductResolver:
    async def resolve_batch(self, normalized_items: list[NormalizedItem]) -> list[StructuredItem]:
        """
        Optimized batch resolution:
        1. All Autocomplete API calls in parallel
        2. Build structured items (CPU-bound)
        3. Apply confidence scoring
        """
```

**Confidence Scoring Rules:**

| Level | Criteria | SKU? | needs_specification? |
|-------|----------|------|---------------------|
| **HIGH** | Exact match in top 3 results + brand specified | ✅ Yes | ❌ No |
| **HIGH** | Exact match in top 3 results + no brand | ❌ No | ✅ Yes |
| **MEDIUM** | Partial match in top 5 results | ❌ No | ✅ Yes |
| **LOW** | No meaningful match | ❌ No | ✅ Yes |

**Brand Option Building:**

When `needs_specification` is true, the resolver builds options from API suggestions:

```python
options = []
for suggestion in api_suggestions[:5]:
    if suggestion.brand and base_product in suggestion.name.lower():
        options.append(ProductOption(
            sku=suggestion.sku,
            name=suggestion.name,
            brand=suggestion.brand,
            image_url=suggestion.image_url
        ))
```

---

#### Image Service

**File:** `app/services/image_service.py`

Fetches product images from OpenFoodFacts (public API).

```python
class ImageService:
    async def get_product_image(self, product_name: str) -> str | None:
        """
        Search OpenFoodFacts for product image.
        Returns None if not found (UI shows placeholder).
        Timeout: 2 seconds for speed.
        """
```

> **Note:** Image fetching is currently disabled in batch processing for speed. Images come from the Autocomplete API response instead.

---

### Models & Schemas

**File:** `app/models/schemas.py`

All Pydantic models for data validation.

#### Input Models

```python
class ParseListRequest(BaseModel):
    text: str  # Raw user input

class ParseListResponse(BaseModel):
    items: list[StructuredItem]
```

#### Internal Models

```python
class NormalizedItem(BaseModel):
    normalized_product_name: str
    quantity: int | float | None = None
    unit: str | None = None
    modifiers: list[str] = []
    notes: str = ""
    original_text: str = ""
    has_brand: bool = False

class AutocompleteProduct(BaseModel):
    sku: str
    name: str
    brand: str | None = None
    category: str | None = None
    image_url: str | None = None
    size: str | None = None
    type_id: str | None = None
    type_name: str | None = None

class ResolvedProduct(BaseModel):
    product_name: str
    sku: str | None = None
    category: str | None = None
    image_url: str | None = None
    brand: str | None = None
    size: str | None = None
    confidence: ConfidenceLevel
    needs_specification: bool = False
    api_suggestions: list[AutocompleteProduct] = []
```

#### Output Models

```python
class ProductOption(BaseModel):
    sku: str
    name: str
    brand: str | None = None
    image_url: str | None = None

class StructuredItem(BaseModel):
    product_name: str
    sku: str | None = None
    quantity: int | float | None = None
    unit: str | None = None
    category: str | None = None
    image_url: str | None = None
    brand: str | None = None
    size: str | None = None
    notes: str = ""
    needs_specification: bool = False
    options: list[ProductOption] = []
```

---

## Frontend (Next.js)

### Pages

#### Home Page (`/`)

**File:** `frontend/src/app/page.tsx`

Dashboard showing:
- Active grocery lists
- Recent lists
- "Create New List" button

#### New List Page (`/list/new`)

**File:** `frontend/src/app/list/new/page.tsx`

List creation with:
- Quick Add Sheet for input
- Items grouped by category
- Brand Selection when tapping items
- Save functionality

#### List Detail Page (`/list/[id]`)

**File:** `frontend/src/app/list/[id]/page.tsx`

View/edit existing list with same features as new list page.

---

### Components

#### QuickAddSheet

**File:** `frontend/src/components/QuickAddSheet.tsx`

Bottom sheet for rapid item entry.

**Features:**
- Multi-line text input
- Live preview of parsed items
- "Processing..." state during API call
- Adds items to list on submit

**Props:**
```typescript
interface QuickAddSheetProps {
  isOpen: boolean;
  onClose: () => void;
  onAddItems: (items: GroceryItem[]) => void;
  listName: string;
}
```

---

#### GroceryItem

**File:** `frontend/src/components/GroceryItem.tsx`

Individual grocery item display.

**Features:**
- Checkbox for completion
- Product name with quantity
- Pills for "Note", "Qty", "Specify"
- Product image (with fallback)
- Click to open specification sheet

**Props:**
```typescript
interface GroceryItemProps {
  item: GroceryItem;
  onToggle: (id: string) => void;
  onSelect: (item: GroceryItem) => void;
}
```

---

#### BrandSelectSheet

**File:** `frontend/src/components/BrandSelectSheet.tsx`

Brand selection bottom sheet.

**Features:**
- Shows when `needs_specification` is true
- Searchable list of brand options
- Product images for each brand
- Updates item when brand selected

**Props:**
```typescript
interface BrandSelectSheetProps {
  isOpen: boolean;
  item: GroceryItem | null;
  onClose: () => void;
  onSelectBrand: (selectedOption: ProductOption) => void;
}
```

---

#### ItemSpecSheet

**File:** `frontend/src/components/ItemSpecSheet.tsx`

Item detail/specification sheet.

**Features:**
- Large product image
- Editable quantity, unit, notes
- "Which one?" section with brand options
- Save/update functionality

---

#### CategorySection

**File:** `frontend/src/components/CategorySection.tsx`

Groups items by category.

```typescript
interface CategorySectionProps {
  category: string;
  items: GroceryItem[];
  onToggleItem: (id: string) => void;
  onSelectItem: (item: GroceryItem) => void;
}
```

---

### API Client

**File:** `frontend/src/lib/api.ts`

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function parseGroceryList(text: string): Promise<ParseListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/parse-list`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  return response.json();
}
```

---

### Styling

**Tailwind Configuration:** `frontend/tailwind.config.ts`

Custom design tokens:

```typescript
colors: {
  primary: '#10B981',           // Green accent
  'primary-hover': '#059669',
  'background-light': '#F9FAFB',
  'background-dark': '#111827',
  'surface-light': '#FFFFFF',
  'surface-dark': '#1F2937',
  'text-main': '#111827',
  'text-sub': '#6B7280',
}

fontFamily: {
  sans: ['SF Pro Display', 'Inter', 'sans-serif'],
}
```

---

## API Reference

### POST /api/v1/parse-list

Parse raw grocery text into structured items.

**Request:**
```http
POST /api/v1/parse-list
Content-Type: application/json

{
  "text": "butter, 2 eggs, milk 2%, tomato paste 8oz"
}
```

**Response:**
```json
{
  "items": [
    {
      "product_name": "Butter",
      "sku": null,
      "quantity": null,
      "unit": null,
      "category": "Dairy",
      "image_url": "https://images.basketsavings.com/...",
      "brand": null,
      "size": null,
      "notes": "",
      "needs_specification": true,
      "options": [
        {
          "sku": "12345",
          "name": "Kerrygold Pure Irish Butter",
          "brand": "Kerrygold",
          "image_url": "https://images.basketsavings.com/..."
        },
        {
          "sku": "12346",
          "name": "Land O'Lakes Salted Butter",
          "brand": "Land O'Lakes",
          "image_url": "https://images.basketsavings.com/..."
        }
      ]
    },
    {
      "product_name": "Farmhouse Eggs",
      "sku": "67890",
      "quantity": 2,
      "unit": null,
      "category": "Dairy & Eggs",
      "image_url": "https://images.basketsavings.com/...",
      "brand": "Farmhouse",
      "size": null,
      "notes": "",
      "needs_specification": false,
      "options": []
    }
  ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `product_name` | string | Resolved product name (autocompleted) |
| `sku` | string \| null | Product SKU (only if HIGH confidence + brand specified) |
| `quantity` | number \| null | Extracted quantity |
| `unit` | string \| null | Unit of measurement |
| `category` | string \| null | Product category from API |
| `image_url` | string \| null | Product image URL |
| `brand` | string \| null | Brand name if identified |
| `size` | string \| null | Product size |
| `notes` | string | Uncertainty notes |
| `needs_specification` | boolean | True if user should select a brand |
| `options` | array | Brand options for selection |

---

## Performance Optimizations

### Before vs After

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| 4 items | 40+ sec | **8 sec** | 5x faster |
| 20 items | 57 sec | **16 sec** | 3.5x faster |
| 30 items | - | **22 sec** | Scales well |

### Optimizations Applied

1. **Single LLM Call**
   - Combined parsing + normalization into one request
   - Reduced from 2 LLM calls to 1

2. **Minimal Prompt**
   - Shortened prompt tokens by 70%
   - Uses abbreviated JSON keys (n, q, u, m, b)

3. **Parallel API Calls**
   - All Autocomplete queries run via `asyncio.gather()`
   - 20 items resolve in ~same time as 1 item

4. **No Image Fetch During Parse**
   - Images come from Autocomplete API response
   - UI shows placeholders for missing images

5. **Batch Processing**
   ```python
   async def resolve_batch(self, items):
       # Step 1: All API calls in parallel
       api_tasks = [self.autocomplete_client.search(q) for q in queries]
       all_suggestions = await asyncio.gather(*api_tasks)
       
       # Step 2: Build items (CPU-bound, fast)
       for i, item in enumerate(items):
           structured = self._build_item(item, all_suggestions[i])
   ```

---

## Testing

**File:** `tests/test_pipeline.py`

Run tests:
```bash
pytest tests/ -v
```

### Test Categories

1. **Unit Tests**
   - Schema validation
   - Confidence scoring logic
   - Safe fallback behavior

2. **Integration Tests**
   - Full pipeline with mock API
   - LLM response handling

### Example Test

```python
class TestConfidenceScoring:
    def test_high_confidence_with_exact_match(self):
        """HIGH confidence when exact product match found."""
        resolver = ProductResolver()
        # ... test implementation
```

---

## Environment Setup

### Backend Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
echo "GEMINI_API_KEY=your_key_here" > .env
echo "AUTOCOMPLETE_AUTH_TOKEN=your_token" >> .env
echo "AUTOCOMPLETE_LAT=44.8828" >> .env
echo "AUTOCOMPLETE_LNG=-93.2007" >> .env

# 4. Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 4. Run development server
npm run dev
```

### Required Environment Variables

**Backend (`.env`):**
```env
GEMINI_API_KEY=AIzaSy...
AUTOCOMPLETE_AUTH_TOKEN=adc3d49185744f4389a2183e694060b9
AUTOCOMPLETE_LAT=44.8828
AUTOCOMPLETE_LNG=-93.2007
```

**Frontend (`frontend/.env.local`):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Future Enhancements (V2+)

- [ ] Voice input (STT)
- [ ] Conversational memory
- [ ] User personalization
- [ ] Price comparison
- [ ] Learning from corrections
- [ ] Offline mode
- [ ] Push notifications
- [ ] List sharing

---

**Built with ❤️ by BasketSavings**
