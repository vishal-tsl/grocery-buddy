"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { BottomToolbar } from "@/components/BottomToolbar";
import { QuickAddSheet } from "@/components/QuickAddSheet";
import { WholeFeedbackBanner } from "@/components/WholeFeedbackBanner";
import { GroceryItem as GroceryItemComponent } from "@/components/GroceryItem";
import { GroceryItem } from "@/types";

export default function NewListPage() {
  const router = useRouter();
  const [items, setItems] = useState<GroceryItem[]>([]);
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(true); // Open by default
  const [lastAddedBatch, setLastAddedBatch] = useState<{ rawInput: string; itemCount: number } | null>(null);
  const [listName] = useState(() => {
    const now = new Date();
    return `Groceries, ${now.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
  });

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
        {/* Whole feedback banner after adding items */}
        {lastAddedBatch && (
          <WholeFeedbackBanner
            rawInput={lastAddedBatch.rawInput}
            itemCount={lastAddedBatch.itemCount}
            onDismiss={() => setLastAddedBatch(null)}
          />
        )}
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

        {/* Plain list of items */}
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
