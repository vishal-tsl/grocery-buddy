# SLAI — Architecture & Decision Log

**Repository:** [github.com/basketsavings/slai](https://github.com/basketsavings/slai)  
**Last Updated:** March 2026

This document explains *why* the system is built the way it is. Every significant design choice is recorded here with the trade-offs that were considered. Think of this as the reasoning layer behind the code.

---

## Table of Contents

1. [Core Philosophy](#core-philosophy)
2. [LLM Agent Design Decisions](#llm-agent-design-decisions)
3. [Confidence Scoring & Guardrails](#confidence-scoring--guardrails)
4. [Product Resolution Strategy](#product-resolution-strategy)
5. [Brand Detection & `has_brand`](#brand-detection--has_brand)
6. [Image Handling](#image-handling)
7. [API Design](#api-design)
8. [Frontend Architecture](#frontend-architecture)
9. [Performance Decisions](#performance-decisions)
10. [Deployment Architecture](#deployment-architecture)
11. [What Was Explicitly Left Out (V1 Scope)](#what-was-explicitly-left-out-v1-scope)
12. [Known Trade-offs & Future Improvements](#known-trade-offs--future-improvements)

---

## Core Philosophy

### Decision: LLMs reason about language; APIs decide on products; code enforces correctness

**Why:** The single biggest failure mode for AI grocery tools is hallucination — inventing a product or SKU that doesn't exist. The system avoids this by strictly separating concerns:

| Concern | Owner | Why |
|---------|-------|-----|
| Understanding messy text | LLM (Gemini) | LLMs are excellent at this |
| Knowing which products exist | Autocomplete API | It's a real product database |
| Enforcing output correctness | Deterministic code | Code can be tested and guaranteed |

The LLM is never asked "what is the SKU for butter?" — it's only asked "what product is the user talking about?". The product database answers the SKU question, and code decides whether to trust the answer.

---

## LLM Agent Design Decisions

### Decision: Two separate agents (Parser + Normalizer) instead of one combined call

**Why:** The Parser and Normalizer have different jobs with different error modes:

- **Parser** removes conversational noise and handles clarification deduplication ("some chicken, like chicken breast" → one item). This requires understanding *conversational context across the whole input*.
- **Normalizer** extracts structured fields from *a single item string*. It needs to decide if "Kerrygold" is a brand or a place name, whether "8oz" is a quantity or a note, etc.

Combining them into one call would make the prompt much larger and harder to test. Failures in one task wouldn't be isolatable. The two-agent design means each prompt can be optimized and tested independently.

**Trade-off:** Two logical agents means two categories of prompts to maintain. In production the Normalizer always uses batch mode (one LLM call for all items), so the latency cost is still just two LLM calls total regardless of list length.

---

### Decision: Gemini 2.0 Flash as the model

**Why:**
- Fast — Flash variants are optimized for latency, which matters in a user-facing parsing pipeline
- Cost-effective at the expected request volume
- The tasks (structured extraction, typo fixing, deduplication) don't require the deepest reasoning; they require reliable instruction-following, which Flash handles well

**What was considered:** GPT-4o Mini would be a direct alternative. Gemini Flash was chosen because the project uses Google infrastructure and the `google-genai` SDK gives a clean Python interface.

---

### Decision: Temperature = 0 for all parsing/normalization calls

**Why:** Grocery list parsing is a deterministic extraction task. The same input ("kerrygold butter") should always produce the same output (`{"normalized_product_name": "Kerrygold butter", "has_brand": true, ...}`). Temperature 0 eliminates variability.

**Exception:** The Recipe agent uses temperature 0.3 when *generating* an ingredient list from a recipe name. Here a small amount of creativity is appropriate because the model is generating plausible content, not extracting facts.

---

### Decision: Batch normalization (all items in one LLM call)

**Why:** After the Parser splits input into N items, naively calling the Normalizer N times would cost N LLM round-trips. For a 20-item list this would add ~40 seconds. Instead, all items are passed to the Normalizer in a single call with a numbered list, and the model returns a JSON array of N objects.

**Failure handling:** If the batch call fails (e.g. the model returns malformed JSON), the code falls back to processing each item individually. This is the correct graceful degradation — slower but correct.

---

### Decision: Strict JSON-only output from the LLM

**Why:** Every prompt ends with "Return ONLY the JSON object/array, no other text." This makes response parsing reliable and avoids the need for complex response extraction logic.

**Code defense:** Even with this instruction, models sometimes wrap output in markdown code fences (` ```json ... ``` `). The code strips these:
```python
if response_text.startswith("```"):
    lines = response_text.split("\n")
    response_text = "\n".join(lines[1:-1])
```
This is a necessary defensive pattern, not a sign of prompt weakness.

---

### Decision: Recipe endpoint disabled at route level, agent code retained

**Why:** The `/recipe-to-list` endpoint was built and tested but disabled before the initial deployment. The code in `app/agents/recipe.py` is kept because:
1. The agent logic is complete and tested
2. Re-enabling requires only restoring imports in `routes.py`
3. Removing it would lose work

The route comment documents exactly what to restore:
```python
# Recipe module temporarily disabled.
# To re-enable, restore RecipeRequest/RecipeResponse imports,
# the get_recipe_agent import, and the /recipe-to-list endpoint below.
```

---

## Confidence Scoring & Guardrails

### Decision: Three-tier confidence (HIGH / MEDIUM / LOW) instead of a continuous score

**Why:** A continuous score would require tuning thresholds. Three named tiers map directly to user-facing behaviors:

| Level | What it means for the user |
|-------|---------------------------|
| HIGH | The system is confident — show the result, optionally include SKU |
| MEDIUM | Partial match — show the result but don't commit to a SKU |
| LOW | The system is guessing — show the result but flag it in notes |

Each tier has a specific numeric value (`0.95`, `0.75`, `0.45`) that the frontend can use for display. The names make the code readable; the numbers make the frontend flexible.

---

### Decision: SKU is never included unless confidence is HIGH

**File:** `app/services/resolver.py` → `_build_structured_item()`

```python
sku=resolved.sku if resolved.confidence == ConfidenceLevel.HIGH else None
```

**Why:** A wrong SKU is worse than no SKU. If the resolver has any doubt (MEDIUM or LOW confidence), the SKU is omitted entirely. The product name is still shown, but the downstream system can't accidentally attach the wrong product to a shopping cart.

Additionally, even at HIGH confidence, the SKU is only kept if it's a "real" API SKU — not a synthetic composite key that the client code generates for keyword-type suggestions:

```python
not suggestion.sku.startswith(("brand_", "type_", "item_"))
```

---

### Decision: Confidence matching checks top 3 (HIGH) and top 5 (MEDIUM) results

**Why:** The first result from the Autocomplete API is not always the best match, but going beyond position 5 for confident matches risks accepting weak results. The cutoffs are empirically chosen:
- Position 1-3: likely the API considered these direct matches
- Position 4-5: still relevant but with less certainty
- Position 6+: used only for building the options list, not for auto-selection

---

### Decision: `needs_specification = true` whenever the user didn't name a brand

**Why:** When a user says "butter," they have not told the system which brand they want. Presenting Kerrygold as the answer would be presumptuous — the user might want Land O'Lakes, or a store brand. By setting `needs_specification=true`, the UI is instructed to surface the choice to the user.

When the user says "Kerrygold butter," `has_brand=true`, so `needs_specification=false` — the system knows exactly what was asked for.

---

## Product Resolution Strategy

### Decision: Autocomplete API is the single source of truth for products

**Why:** The Autocomplete API (BasketSavings) is a real product database with real SKUs. Any other source (OpenFoodFacts, a generic web search, or the LLM's training data) would introduce products that may not be available in the actual shopping context.

The system is deliberately opinionated: if the Autocomplete API doesn't have it, the item is returned with `sku=null` and `confidence=LOW`, not invented.

---

### Decision: Parallel API calls for all items via `asyncio.gather`

**File:** `app/services/resolver.py` → `resolve_batch()`

```python
api_tasks = [self.autocomplete_client.search(q) for q in search_queries]
all_suggestions = await asyncio.gather(*api_tasks)
```

**Why:** Each item's Autocomplete API call is independent. Running them in parallel reduces total resolution time from O(N) to O(1) (limited by the slowest single call). For a 20-item list, this saves ~15 seconds.

---

### Decision: Always use the first suggestion in filtered candidate order

**File:** `app/services/resolver.py` → `_pick_best_suggestion()`

```python
def _pick_best_suggestion(self, candidates):
    if not candidates:
        return None
    return candidates[0]
```

**Why:** The API returns results in relevance order. The first result is always the most relevant according to the API. Re-ranking by any other criteria (e.g. preferring a branded product over a keyword) risks showing a name that doesn't match the product image. API order is used as-is to keep name and image in sync.

---

### Decision: `selected_option_index` and `selected_suggestion_index` are both tracked

**Why:** These serve different purposes in the UI:

- `selected_option_index`: the 1-based position in the `options[]` array that was auto-selected. Used to highlight the correct option in a brand-picker UI.
- `selected_suggestion_index`: the 1-based position in the raw API results (e.g. "Option 3 of 20"). Used in a developer/debug chip on each item so engineers can see how the matching worked at a glance.

---

### Decision: Brand variations are built from all API suggestions, not just top-3

**Why:** A user asking for "butter" should see all available butter brands, not just the top 3. The options list is built from all API suggestions (up to the API's limit, typically 20), with deduplication by SKU. The UI renders as many as the API provides.

---

### Decision: Compound-word exclusion in brand option building

**File:** `app/services/resolver.py` → `_build_structured_item()`

```python
if words_before in ["peanut", "almond", "cashew", "sunflower", "apple", "coconut", "soy"]:
    continue
```

**Why:** When a user asks for "butter," the "same product" check looks for API suggestions whose name contains "butter." Without this exclusion, "Peanut Butter" would appear as a brand option for "butter," since "butter" appears in the name. The exclusion list covers known compound products where the base word is part of a different product category.

---

## Brand Detection & `has_brand`

### Decision: Brand detection is done by the LLM Normalizer, not by a lookup list

**Why:** Brand names are a long tail. Maintaining a hardcoded lookup list would require constant updates and would miss new or niche brands. The LLM is better at recognizing proper nouns in context:

- "Kerrygold butter" → the LLM recognizes "Kerrygold" as a proper noun brand
- "Dijon mustard" → the LLM knows "Dijon" is a French city/style, not a brand
- "portobello mushroom" → the LLM knows "portobello" is a variety, not a brand

The Normalizer prompt provides many labeled examples to calibrate this distinction.

---

### Decision: `has_brand` is a boolean, not the brand name itself

**Why:** Simplicity. The brand name is already embedded in the `normalized_product_name` when `has_brand=true` (e.g. "Kerrygold butter"). Extracting it separately would require more parsing logic with no benefit at the resolver level.

---

### Decision: Brand image safety check uses fuzzy matching with stop-word stripping

**File:** `app/services/resolver.py` → `_brand_matches()`

**Why:** Brand names in the API often have legal suffixes ("The Happy Egg Co.", "Land O'Lakes, Inc.") that the user would never type. A raw string equality check would fail. The matcher strips common legal suffixes and also tries matching by first significant word, handling cases like "Kerrygold" matching "Kerrygold Pure Irish Butter."

---

## Image Handling

### Decision: Images come exclusively from the Autocomplete API (BasketSavings)

**Why:** Earlier versions fetched images from OpenFoodFacts as a fallback. This was removed because:
1. OpenFoodFacts images are community-contributed and variable in quality
2. A third fetch per item added latency
3. The Autocomplete API already returns image URLs as part of the product data

The frontend `image.ts` utility enforces this: it explicitly returns `undefined` for any non-BasketSavings URL:
```typescript
// Other absolute URLs → not used (BasketSavings only)
if (uri.startsWith("https://") || uri.startsWith("http://")) {
    return undefined;
}
```

---

### Decision: Image proxy endpoint is included but not the primary image path

**File:** `app/api/image_proxy.py`

**Why:** The image proxy (`GET /api/v1/image-proxy?url=...`) was built to handle cases where BasketSavings images require authentication headers. In practice, most images load directly from the CDN without authentication. The proxy is available as a fallback but is not called by default.

**Security guard:** The proxy validates that the URL is a BasketSavings URL before fetching:
```python
if not url.startswith("https://images.basketsavings.com/"):
    raise HTTPException(status_code=400, detail="Only basketsavings images allowed")
```
This prevents the endpoint from being used as an open proxy.

---

### Decision: Images are displayed at two sizes (thumbnail `s`, full `l`)

**File:** `frontend/src/lib/image.ts`

| Size key | Pixels | Used for |
|----------|--------|---------|
| `xs` | 50 | (reserved) |
| `s` | 100 | Thumbnail in list row |
| `m` | 400 | (reserved) |
| `l` | 900 | Full-size popup |

The `img.basketsavings.com` CDN accepts `width` and `height` parameters, so the frontend requests exactly the resolution needed rather than downloading a large image for a small thumbnail.

---

### Decision: Image load errors are handled silently with an icon placeholder

**Why:** A broken image should not break the UI or show an error state to the user. The `GroceryItem` component tracks `thumbError` state and shows a generic image icon when loading fails:
```tsx
const [thumbError, setThumbError] = useState(false);
// ...
onError={() => setThumbError(true)}
```

---

## API Design

### Decision: Single endpoint `/api/v1/parse-list` for all grocery text input

**Why:** The pipeline (parse → normalize → resolve) is always run in full. There's no use case for running only the parser or only the resolver from outside the system. One endpoint means one contract to document and maintain.

---

### Decision: `match_source` and `match_reason` included in every item response

**Why:** These fields are primarily for debugging and transparency, not for the end user. They allow an engineer to inspect why a specific product was selected:
- `match_source: "product"` — a real SKU match
- `match_source: "keyword"` — a category-level match
- `match_source: "ai_text"` — no API match, AI-normalized text only
- `match_reason` — human-readable explanation (e.g. `"product (SKU 1234): Kerrygold Butter"`)

The frontend renders these as small debug chips visible during development.

---

### Decision: CORS is configured to allow any HTTP/HTTPS origin via regex

**File:** `app/main.py`

```python
allow_origin_regex=r"https?://[^/]+"  # any http(s) origin
```

**Why:** The frontend may be deployed on multiple Vercel preview URLs, a custom domain, or localhost. Maintaining an explicit allow-list would require updates on every new deployment. The regex allows any origin while still blocking non-HTTP(S) schemes.

**Trade-off:** This is permissive. For a production API that handles sensitive data, a stricter allow-list would be appropriate. For a grocery list tool, it's acceptable.

---

### Decision: Fallback response when the whole endpoint fails

**File:** `app/api/routes.py`

```python
except Exception as e:
    for item in request.text.replace("\n", ",").split(","):
        fallback_items.append(StructuredItem(
            product_name=item,
            notes="Processing failed"
        ))
```

**Why:** An error in the LLM or API layer should never return a 500 to the user. The fallback splits the input by commas and newlines, treating each segment as a raw item name. The user gets something back that they can work with, with a `notes` field indicating processing failed.

---

## Frontend Architecture

### Decision: Next.js App Router (not Pages Router)

**Why:** New Next.js projects should use the App Router. Server Components, improved layouts, and nested routing are available out of the box. The project uses mostly Client Components (`"use client"`) because the grocery list state is highly interactive, but the router structure benefits from App Router conventions.

---

### Decision: No external state management library (no Redux, no Zustand)

**Why:** The app's state is simple: a list of items per page. React's `useState` handles this without ceremony. Adding a global state library for a single list would introduce complexity that doesn't buy anything.

**Trade-off:** List state is lost on navigation. This is acceptable for V1 since lists are not persisted to a backend yet. If persistence is added, a state library or server state tool (like React Query) would become appropriate.

---

### Decision: Framer Motion for sheet animations

**Why:** The bottom sheet pattern (QuickAdd, BrandSelect, ItemSpec) requires spring physics for a native mobile feel. Framer Motion provides this without writing raw CSS animations:

```tsx
<motion.div
  initial={{ y: "100%" }}
  animate={{ y: 0 }}
  exit={{ y: "100%" }}
  transition={{ type: "spring", damping: 30, stiffness: 300 }}
>
```

**Trade-off:** Framer Motion adds ~60KB to the bundle. For a mobile-first app where the sheet animation is a core UX element, this is justified.

---

### Decision: Live item preview in QuickAddSheet is client-side only (no API call)

**File:** `frontend/src/components/QuickAddSheet.tsx`

```typescript
const lines = text.split(/[\n,]/).map(l => l.trim()).filter(l => l.length > 0);
setParsedItems(lines);
```

**Why:** Showing a live count/preview of items as the user types gives immediate feedback without any latency. The real AI parsing happens only on submit. A debounced API call on every keystroke would be unnecessarily expensive and introduce lag.

---

### Decision: QuickAddSheet has a frontend fallback if the API call fails

```typescript
catch (error) {
    const fallbackItems = parsedItems.map(text => ({
        product_name: text,
        sku: null,
        // ...
        match_source: "ai_text",
    }));
    onAddItems(fallbackItems);
}
```

**Why:** A network failure or API timeout should not lose the user's typed input. The fallback adds the raw text segments as unstructured items, so the user's list is preserved even if AI parsing failed. They can manually edit the items after.

---

### Decision: Image URL is routed through `urlImageProvider` utility on the frontend

**File:** `frontend/src/lib/image.ts`

**Why:** This utility is the single place that controls:
1. Which image sources are trusted (BasketSavings only)
2. What size variant is requested (`s` vs `l`)
3. How path-only image IDs are converted to full URLs

Centralizing this means a change to the image CDN hostname only requires one file change, not hunting through every component.

---

### Decision: Brand line is hidden for keyword-matched items

**File:** `frontend/src/components/GroceryItem.tsx`

```typescript
const brand = item.match_source === "keyword" ? null : (item.brand ?? ...);
```

**Why:** Keyword matches (e.g. "Milk" as a category/type) have brand suggestions in their options, but the `brand` field at the item level reflects the first suggestion, which may be unrelated. Showing that brand as a subtitle would be misleading. Keyword items show only the product name.

---

### Decision: Debug chips (match_source, confidence, autocomplete_query) are always rendered

**Why:** During V1 the primary users are engineers testing the system. Showing the match source, confidence score, autocomplete query, and option index directly in the item list makes it fast to spot mismatches without opening developer tools or reading API responses. These can be hidden behind a flag in a future consumer-facing release.

---

## Performance Decisions

### Summary of optimizations and their rationale

| Optimization | Location | Benefit |
|-------------|----------|---------|
| Batch normalization | `normalizer.py` | 1 LLM call instead of N |
| Parallel API calls | `resolver.py` | O(1) instead of O(N) API latency |
| No image fetches at parse time | `resolver.py` | Images come from Autocomplete response |
| JSON-LD extraction before LLM | `recipe.py` | Skip LLM if structured data available |
| HTML truncation at 15K chars | `recipe.py` | Avoid token limit / cost on large recipe pages |
| Temperature = 0 | All agents | Faster (no sampling), deterministic |
| Singleton agent instances | All agents | No re-instantiation per request |

**Measured latencies (approximate):**

| List size | LLM time | API time | Total |
|-----------|----------|----------|-------|
| 4 items | ~5s | ~2s | ~8s |
| 20 items | ~8s | ~3s | ~16s |
| 30 items | ~11s | ~4s | ~22s |

The LLM call is the dominant cost. Further improvements would come from caching common items or using a faster model.

---

## Deployment Architecture

### Decision: Frontend on Vercel, backend on Railway or Render (not both on Vercel)

**Why:** Vercel's Python support (serverless functions) has known limitations with FastAPI:
- Long-running requests hit the default 10s serverless timeout
- The build system sometimes fails to create runnable functions, resulting in 404s
- Cold starts add unpredictable latency

Railway and Render run the app as a persistent process (`uvicorn app.main:app`), which avoids all of these issues. The frontend (Next.js) is a first-class Vercel target and deploys without issues.

This is documented prominently in `DEPLOYMENT.md`:
> "The backend (FastAPI) often does not run correctly on Vercel... Use Railway or Render for the backend."

---

### Decision: Two separate Vercel projects for frontend and backend (when using Vercel for backend)

**Why:** Vercel determines the project type from the root directory. The same repo has a Next.js app at `frontend/` and a Python app at the root. Vercel cannot deploy both from one project — you must set the root directory per project. Two projects from the same repo is the standard Vercel pattern for monorepos.

---

### Decision: `NEXT_PUBLIC_API_URL` for backend URL, no hardcoding

**Why:** The frontend needs to call the backend. The URL changes between local development, staging, and production. `NEXT_PUBLIC_API_URL` is a Next.js convention for environment-specific public variables. A trailing slash is stripped in the API client to prevent double-slash URLs:

```typescript
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
```

---

## What Was Explicitly Left Out (V1 Scope)

These are not oversights — they were deliberately deferred:

| Feature | Reason deferred |
|---------|-----------------|
| **Voice input (STT)** | Adds mobile browser complexity; text input covers the core use case |
| **Conversational memory** | No user accounts; each request is stateless |
| **Personalization** | No user accounts; preferences can't be stored |
| **Price comparison** | Requires prices from multiple retailers; out of scope for the structuring engine |
| **Learning from corrections** | No feedback loop infrastructure; would require user accounts |
| **Vector DB / embeddings** | The Autocomplete API already handles semantic search; embeddings would duplicate it |
| **List persistence** | No backend database for user data; lists live in browser memory only |
| **Offline mode** | Requires service workers and significant frontend work |
| **List sharing** | Requires list persistence and user identity |

---

## Known Trade-offs & Future Improvements

### LLM latency is the bottleneck

The two LLM calls (parse + normalize) take 5–11 seconds for typical lists. Options to reduce this:
1. **Cache normalized items** — common items like "eggs" or "milk" don't need LLM processing every time
2. **Streaming response** — return items to the frontend as they resolve rather than waiting for all
3. **Smaller model** — if a distilled or fine-tuned model can match quality, latency drops dramatically

### List state is not persisted

The frontend stores list state in React `useState`. Navigating away or refreshing loses everything. A future version would persist to localStorage (no-auth option) or a user account backend.

### `needs_specification` has no UI action in the current list view

The `needs_specification` flag is set correctly and the `options` array is populated, but the current list page does not render a brand-picker sheet. The `BrandSelectSheet` component exists but is not wired into the list flow. This is the highest-priority UX gap.

### Recipe feature is disabled but fully implemented

The `RecipeAgent` in `app/agents/recipe.py` is complete. The route was disabled before the initial release. Re-enabling requires restoring three lines in `app/api/routes.py` (documented in the comment at the bottom of that file).
