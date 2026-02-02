export interface ProductOption {
  sku: string;
  name: string;
  brand: string | null;
  image_url: string | null;
}

export interface GroceryItem {
  id: string;
  product_name: string;
  sku: string | null;
  quantity: number | null;
  unit: string | null;
  notes: string;
  checked: boolean;
  category?: string;
  image_url?: string;
  brand?: string | null;
  size?: string | null;
  needs_specification?: boolean;
  options?: ProductOption[];
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
  }>;
}
