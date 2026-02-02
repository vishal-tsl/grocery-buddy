# Grocery List Structuring Engine V1

AI-powered engine that converts unstructured grocery input into clean, structured shopping lists.

## Overview

This system accepts raw grocery text input (copy-paste or typed text) and outputs a structured shopping list with:
- Normalized product names
- SKUs (only when confidently matched via API)
- Quantities and units
- Notes capturing any uncertainty

**Key Principles:**
- LLMs reason about language
- APIs decide on products (Autocomplete API is the ONLY source of truth)
- Code enforces correctness
- No hallucinated products or SKUs

## Architecture

```
Raw User Input
     ↓
Parser Agent (Gemini LLM)
     ↓
Normalizer Agent (Gemini LLM)
     ↓
Autocomplete API (deterministic)
     ↓
Confidence & Guardrails (code)
     ↓
Structured List Output
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.template` to `.env` and fill in your credentials:

```bash
cp .env.template .env
```

Required environment variables:
- `GEMINI_API_KEY` - Your Google Gemini API key
- `AUTOCOMPLETE_AUTH_TOKEN` - Authorization token for Autocomplete API
- `AUTOCOMPLETE_LAT` - Latitude for location-based results
- `AUTOCOMPLETE_LNG` - Longitude for location-based results

### 3. Run the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Usage

### POST /api/v1/parse-list

Parse raw grocery text into a structured list.

**Request:**
```json
{
  "text": "tomato paste 8oz\nmilk 2%\nidk some chips\nbread maybe wheat"
}
```

**Response:**
```json
{
  "items": [
    {
      "product_name": "Hunt's Tomato Paste 8oz",
      "sku": "12345",
      "quantity": 8,
      "unit": "oz",
      "notes": ""
    },
    {
      "product_name": "2% Milk",
      "sku": "67890",
      "quantity": null,
      "unit": null,
      "notes": ""
    },
    {
      "product_name": "Chips",
      "sku": null,
      "quantity": null,
      "unit": null,
      "notes": "User unclear: 'idk some chips'"
    },
    {
      "product_name": "Bread",
      "sku": null,
      "quantity": null,
      "unit": null,
      "notes": "User uncertain: 'maybe wheat'"
    }
  ]
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## Output Contract

Every item conforms to this schema:

| Field | Type | Description |
|-------|------|-------------|
| `product_name` | string | The resolved product name |
| `sku` | string \| null | SKU only if confidently matched via API |
| `quantity` | number \| null | Explicit quantity if provided |
| `unit` | string \| null | Unit of measurement if provided |
| `notes` | string | Any uncertainty or additional context |

## Confidence Scoring

The resolver applies deterministic confidence rules:

| Level | Criteria | Behavior |
|-------|----------|----------|
| **HIGH** | Exact keyword match in top 3 API results | Accept product with SKU |
| **MEDIUM** | Partial or category-level match | Accept generic name, no SKU |
| **LOW** | No meaningful match | Generic name, original text in notes |

## Project Structure

```
slai/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Environment configuration
│   ├── api/
│   │   └── routes.py        # API endpoints
│   ├── agents/
│   │   ├── parser.py        # Gemini-powered input parser
│   │   └── normalizer.py    # Gemini-powered normalizer
│   ├── services/
│   │   ├── autocomplete.py  # Autocomplete API client
│   │   └── resolver.py      # Product resolution + confidence
│   └── models/
│       └── schemas.py       # Pydantic models
├── tests/
│   └── test_pipeline.py     # Unit and integration tests
├── requirements.txt
└── README.md
```

## Running Tests

```bash
pytest tests/ -v
```

## Frontend

A modern Next.js frontend is available in the `frontend/` directory.

### Quick Start

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Features

- **Home Screen**: Dashboard with active and recent lists
- **List View**: Items grouped by category with checkboxes
- **Quick Add**: Bottom sheet for rapid item entry with AI parsing

See `frontend/README.md` for detailed documentation.

## V1 Scope

**In Scope:**
- Text input parsing
- Product normalization
- Autocomplete API resolution
- Confidence scoring
- Safe fallbacks

**Out of Scope (V1):**
- Voice (STT/TTS)
- Conversational memory
- Personalization
- Price optimization
- Product search API
- Vector DBs or embeddings
- Learning from user corrections
