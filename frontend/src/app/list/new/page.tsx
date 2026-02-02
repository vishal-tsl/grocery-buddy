"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { BottomToolbar } from "@/components/BottomToolbar";
import { QuickAddSheet } from "@/components/QuickAddSheet";
import { ItemSpecSheet } from "@/components/ItemSpecSheet";
import { BrandSelectSheet } from "@/components/BrandSelectSheet";
import { CategorySection } from "@/components/CategorySection";
import { GroceryItem, ProductOption } from "@/types";

export default function NewListPage() {
  const router = useRouter();
  const [items, setItems] = useState<GroceryItem[]>([]);
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(true); // Open by default
  const [selectedItem, setSelectedItem] = useState<GroceryItem | null>(null);
  const [isItemSpecOpen, setIsItemSpecOpen] = useState(false);
  const [isBrandSelectOpen, setIsBrandSelectOpen] = useState(false);
  const [brandSelectItem, setBrandSelectItem] = useState<GroceryItem | null>(null);
  const [listName] = useState(() => {
    const now = new Date();
    return `Groceries, ${now.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
  });

  // Group items by category
  const itemsByCategory = items.reduce((acc, item) => {
    const category = item.category || "Other";
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(item);
    return acc;
  }, {} as Record<string, GroceryItem[]>);

  const handleToggleItem = (id: string) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, checked: !item.checked } : item
      )
    );
  };

  const handleAddItems = (newItems: GroceryItem[]) => {
    // Category comes from API - use "Other" only as fallback
    const itemsWithCategory = newItems.map((item) => ({
      ...item,
      category: item.category || "Other",  // API provides category, fallback to "Other"
    }));
    setItems((prev) => [...prev, ...itemsWithCategory]);
  };

  const handleSelectItem = (item: GroceryItem) => {
    setSelectedItem(item);
    setIsItemSpecOpen(true);
  };

  const handleUpdateItem = (updatedItem: GroceryItem) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === updatedItem.id ? updatedItem : item
      )
    );
    setSelectedItem(updatedItem);
  };

  const handleSpecifyItem = (item: GroceryItem) => {
    setBrandSelectItem(item);
    setIsBrandSelectOpen(true);
  };

  const handleSelectBrand = (item: GroceryItem, option: ProductOption) => {
    // Update the item with selected brand
    const updatedItem: GroceryItem = {
      ...item,
      product_name: option.name,
      sku: option.sku,
      brand: option.brand,
      image_url: option.image_url || item.image_url,
      needs_specification: false, // No longer needs specification
    };
    
    setItems((prev) =>
      prev.map((i) => (i.id === item.id ? updatedItem : i))
    );
    setIsBrandSelectOpen(false);
    setBrandSelectItem(null);
  };

  return (
    <div className="flex flex-col min-h-screen bg-background-light dark:bg-background-dark">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 bg-background-light dark:bg-background-dark sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/")}
            className="relative p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          >
            <Icon name="close" size={24} className="text-gray-600 dark:text-gray-300" />
          </button>
          <h1 className="text-xl font-bold text-gray-800 dark:text-white">
            {listName}
          </h1>
        </div>
        <button
          disabled={items.length === 0}
          className="px-4 py-2 bg-primary hover:bg-primary-hover disabled:bg-gray-300 disabled:dark:bg-gray-700 rounded-lg text-white text-sm font-semibold transition-colors"
        >
          Save
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto no-scrollbar pb-32">
        {/* Add items prompt when empty */}
        {items.length === 0 && !isQuickAddOpen && (
          <div className="px-5 py-8">
            <div
              onClick={() => setIsQuickAddOpen(true)}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <div className="w-6 h-6 rounded-full border-2 border-dashed border-gray-300 dark:border-gray-600 group-hover:border-primary transition-colors" />
              <span className="text-lg text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors">
                Add items...
              </span>
            </div>
          </div>
        )}

        {/* Show items grouped by category */}
        {Object.entries(itemsByCategory).map(([category, categoryItems]) => (
          <CategorySection
            key={category}
            category={category}
            items={categoryItems}
            onToggleItem={handleToggleItem}
            onSelectItem={handleSelectItem}
            onSpecifyItem={handleSpecifyItem}
            onSelectBrand={handleSelectBrand}
          />
        ))}
      </main>

      {/* Bottom Toolbar */}
      <BottomToolbar onQuickAdd={() => setIsQuickAddOpen(true)} />

      {/* Quick Add Sheet */}
      <QuickAddSheet
        isOpen={isQuickAddOpen}
        onClose={() => setIsQuickAddOpen(false)}
        onAddItems={handleAddItems}
        listName={listName}
      />

      {/* Item Specification Sheet */}
      <ItemSpecSheet
        isOpen={isItemSpecOpen}
        item={selectedItem}
        onClose={() => {
          setIsItemSpecOpen(false);
          setSelectedItem(null);
        }}
        onUpdate={handleUpdateItem}
      />

      {/* Brand Selection Sheet */}
      <BrandSelectSheet
        isOpen={isBrandSelectOpen}
        item={brandSelectItem}
        onClose={() => {
          setIsBrandSelectOpen(false);
          setBrandSelectItem(null);
        }}
        onSelectBrand={handleSelectBrand}
      />
    </div>
  );
}
