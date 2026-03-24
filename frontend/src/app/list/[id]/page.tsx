"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { GroceryItem as GroceryItemComponent } from "@/components/GroceryItem";
import { WholeFeedbackBanner } from "@/components/WholeFeedbackBanner";
import { BottomToolbar } from "@/components/BottomToolbar";
import { QuickAddSheet } from "@/components/QuickAddSheet";
import { GroceryItem } from "@/types";

// Mock data - in real app, this would come from API/state
const mockItems: GroceryItem[] = [
  {
    id: "1",
    product_name: "Mushrooms",
    sku: "MSH001",
    quantity: null,
    unit: null,
    notes: "",
    checked: false,
    category: "Fresh Produce",
    image_url: "https://images.basketsavings.com/2024/7/5/10/7966c1a7-26ba-42b6-910f-4329049257a7",
    match_source: "product",
  },
  {
    id: "2",
    product_name: "Daisy Sour Cream",
    sku: "DSC001",
    quantity: null,
    unit: null,
    notes: "",
    checked: false,
    category: "Dairy & Eggs",
    match_source: "keyword",
  },
  {
    id: "3",
    product_name: "EggLand's Best Eggs",
    sku: "EGG001",
    quantity: null,
    unit: null,
    notes: "",
    checked: true,
    category: "Dairy & Eggs",
    image_url: "2024/5/23/12/8918b100-c025-42fe-8148-a602ed633019",
    match_source: "ai_text",
  },
  {
    id: "4",
    product_name: "Hamburger",
    sku: null,
    quantity: null,
    unit: null,
    notes: "",
    checked: true,
    category: "Meat & Seafood",
  },
  {
    id: "5",
    product_name: "Sugar",
    sku: null,
    quantity: null,
    unit: null,
    notes: "",
    checked: true,
    category: "Baking & Cooking Needs",
  },
  {
    id: "6",
    product_name: "Tomato Paste",
    sku: "TMP001",
    quantity: 8,
    unit: "oz",
    notes: "",
    checked: false,
    category: "Canned & Jarred Foods",
  },
  {
    id: "7",
    product_name: "Charmin Toilet Paper",
    sku: "CTP001",
    quantity: null,
    unit: null,
    notes: "",
    checked: false,
    category: "Paper Goods & Cleaning Supplies",
    image_url: "https://images.basketsavings.com/2024/7/5/10/7966c1a7-26ba-42b6-910f-4329049257a7",
  },
];

export default function ListPage() {
  const params = useParams();
  const router = useRouter();
  const listId = params.id as string;
  
  const [items, setItems] = useState<GroceryItem[]>(mockItems);
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
  const [lastAddedBatch, setLastAddedBatch] = useState<{ rawInput: string; itemCount: number } | null>(null);

  const handleToggleItem = (id: string) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, checked: !item.checked } : item
      )
    );
  };

  const handleAddItems = (newItems: GroceryItem[], rawInput?: string) => {
    // Category comes from API - use "Other" only as fallback
    const itemsWithCategory = newItems.map((item) => ({
      ...item,
      category: item.category || "Other",  // API provides category, fallback to "Other"
    }));
    setItems((prev) => [...prev, ...itemsWithCategory]);
    if (rawInput) {
      setLastAddedBatch({ rawInput, itemCount: newItems.length });
    }
  };

  const completedCount = items.filter((item) => item.checked).length;
  const totalCount = items.length;

  const listName = listId === "new" ? "New List" : "Groceries, Feb 2";

  return (
    <div className="flex flex-col min-h-screen bg-background-light dark:bg-background-dark">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 bg-background-light dark:bg-background-dark sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/")}
            className="relative p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          >
            <Icon name="arrow_back" size={24} className="text-gray-600 dark:text-gray-300" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-800 dark:text-white">
              {listName}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {completedCount}/{totalCount} items
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition">
            <Icon
              name="person_add"
              size={24}
              className="text-gray-500 dark:text-gray-400"
            />
          </button>
          <button className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition">
            <Icon
              name="more_vert"
              size={24}
              className="text-gray-500 dark:text-gray-400"
            />
          </button>
        </div>
      </header>

      {/* Main Content - plain list */}
      <main className="flex-1 overflow-y-auto no-scrollbar pb-32">
        {lastAddedBatch && (
          <WholeFeedbackBanner
            rawInput={lastAddedBatch.rawInput}
            itemCount={lastAddedBatch.itemCount}
            onDismiss={() => setLastAddedBatch(null)}
          />
        )}
        <div className="flex flex-col">
          {items.map((item) => (
            <GroceryItemComponent
              key={item.id}
              item={item}
              onToggle={handleToggleItem}
              onSelect={() => {}}
            />
          ))}
        </div>

        {items.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
            <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
              <Icon
                name="shopping_cart"
                size={32}
                className="text-gray-400 dark:text-gray-500"
              />
            </div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-2">
              No items yet
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              Tap the button below to add your first items
            </p>
            <button
              onClick={() => setIsQuickAddOpen(true)}
              className="px-6 py-3 bg-primary hover:bg-primary-hover rounded-xl text-white font-semibold transition-colors"
            >
              Add Items
            </button>
          </div>
        )}
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

    </div>
  );
}
