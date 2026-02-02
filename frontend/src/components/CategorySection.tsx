"use client";

import { GroceryItem as GroceryItemType, ProductOption } from "@/types";
import { GroceryItem } from "./GroceryItem";

interface CategorySectionProps {
  category: string;
  items: GroceryItemType[];
  onToggleItem: (id: string) => void;
  onSelectItem: (item: GroceryItemType) => void;
  onSpecifyItem?: (item: GroceryItemType) => void;
  onSelectBrand?: (item: GroceryItemType, option: ProductOption) => void;
}

export function CategorySection({
  category,
  items,
  onToggleItem,
  onSelectItem,
  onSpecifyItem,
  onSelectBrand,
}: CategorySectionProps) {
  return (
    <section className="mt-4">
      <h2 className="px-5 py-3 text-sm font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wide border-b border-gray-200 dark:border-gray-700">
        {category}
      </h2>
      <div className="flex flex-col">
        {items.map((item) => (
          <GroceryItem 
            key={item.id}
            item={item} 
            onToggle={onToggleItem} 
            onSelect={onSelectItem}
            onSpecify={onSpecifyItem}
            onSelectBrand={onSelectBrand}
          />
        ))}
      </div>
    </section>
  );
}
