export interface ProductOption {
  sku: string;
  name: string;
  brand: string | null;
  image_url: string | null;
}

/** How the item was resolved: product key, keyword match, or plain AI text */
export type MatchSource = "product" | "keyword" | "ai_text";

export interface GroceryItem {
  id: string;
  product_name: string;
  sku: string | null;
  quantity: number | null;
  unit: string | null;
  notes: string;
  checked: boolean;
  category?: string;
  image_url?: string | null;
  brand?: string | null;
  size?: string | null;
  needs_specification?: boolean;
  options?: ProductOption[];
  match_source?: MatchSource;
  match_reason?: string;
  /** Mapping quality score, e.g. 0.95 */
  confidence?: number;
  /** 1-based index in options[] that was auto-selected */
  selected_option_index?: number | null;
  /** 1-based index among full API suggestions (e.g. show "Option 3 of 20") */
  selected_suggestion_index?: number | null;
  /** Total suggestions returned by API (e.g. 20) */
  total_suggestions?: number | null;
  /** Phrase/word sent to autocomplete to fetch this item */
  autocomplete_query?: string | null;
}

export interface GroceryList {
  id: string;
  name: string;
  date: string;
  items: GroceryItem[];
  total_items: number;
  completed_items: number;
}

export interface ParseListRequest {
  text: string;
}

export interface ParseListResponse {
  items: Array<{
    product_name: string;
    sku: string | null;
    quantity: number | null;
    unit: string | null;
    category: string | null;
    image_url: string | null;
    brand: string | null;
    size: string | null;
    notes: string;
    needs_specification: boolean;
    options: ProductOption[];
    match_source?: MatchSource;
    match_reason?: string;
    confidence?: number;
    selected_option_index?: number | null;
    selected_suggestion_index?: number | null;
    total_suggestions?: number | null;
    autocomplete_query?: string | null;
  }>;
}

export interface RecipeRequest {
  input: string;
}

export interface RecipeResponse {
  recipe_name: string;
  servings: number | null;
  source: string;
  source_url: string | null;
  ingredients_raw: string[];
  items: Array<{
    product_name: string;
    sku: string | null;
    quantity: number | null;
    unit: string | null;
    category: string | null;
    image_url: string | null;
    brand: string | null;
    size: string | null;
    notes: string;
    needs_specification: boolean;
    options: ProductOption[];
    match_source?: MatchSource;
    match_reason?: string;
  }>;
}
