"use client";

import { useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { CategorySection } from "@/components/CategorySection";
import { BottomToolbar } from "@/components/BottomToolbar";
import { QuickAddSheet } from "@/components/QuickAddSheet";
import { ItemSpecSheet } from "@/components/ItemSpecSheet";
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
    image_url:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuDYMqChevw-OLVxDSfw94biiYKa6rj4L7gblI8kJlOBG3-MkryCPacKiDT_TUqFT_Fc24yRAqVmY5Wh6CNsefweWkpgSO6bEU1uCNzumtd1pahn0LAl6UyevmyduUpy3dObe9beFhMlUWz44WghANA3S2vshLRCP3FtT36NtVk36n4LA-UgVzJle6e8pLVV0jXfcFULAOlSI0PEr41XOsMBBUXGQae-whBXQubro3Hi3XVXbtJY0S9OFADePVQLYtB8ccopmnQEnDiq",
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
    image_url:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuBKyVnIc1i8YCnpJVntzm3TLonx_mIW4IbG3H1PnVxmpaQRub-z0ExEn6M7gxUp1-KrmTOUfBjI5eo_-5c44_IwkSEMHsuE2Q00E41v_hRfXhzOEMbFD4g2-vfwsqJR4FkBflEm47OLgorFPQnJZHiGKbUoQTtm0eaB_pBkfXUSBnbUVneSL0KqUomd9OADlJB7C0ewBXsrIyvogUuq9sVNN6gIZY77DXodHC3FRl1pT5rN1fWN88FD2bSeOXT43mMJY57GfF4Lvk",
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
    image_url:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuDT16cOlTXEwCrvD5UV7t5alm2pn5d88JcnEjeSXMB6dA8QEsqP3wiiqGby7DObWG9D2lJT03wjOMJ_35jLHRWgM1yZJmAlKQF6mSMSaTXwcJTLHjXaglbGRq792L2MD4JveR2A_iLzmdG5HhCd6lbqxSYQGVf3Gw8m3eaej-nj_PqWnBH7-tXfsNXwrdVZ_rPxVVgebAyyiGpJB0VWUipLU4ElohJ9OdJaAZw5pVFPSBjsKGCprQMJdMaVRh2RyGHUiKTN_l0LHEng",
  },
];

// Category order for sorting
const categoryOrder = [
  "Fresh Produce",
  "Dairy & Eggs",
  "Meat & Seafood",
  "Baking & Cooking Needs",
  "Canned & Jarred Foods",
  "Paper Goods & Cleaning Supplies",
  "Other",
];

export default function ListPage() {
  const params = useParams();
  const router = useRouter();
  const listId = params.id as string;
  
  const [items, setItems] = useState<GroceryItem[]>(mockItems);
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<GroceryItem | null>(null);
  const [isItemSpecOpen, setIsItemSpecOpen] = useState(false);

  // Group items by category
  const itemsByCategory = useMemo(() => {
    const grouped: Record<string, GroceryItem[]> = {};
    
    items.forEach((item) => {
      const category = item.category || "Other";
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(item);
    });

    // Sort categories by predefined order
    const sortedCategories = Object.keys(grouped).sort((a, b) => {
      const indexA = categoryOrder.indexOf(a);
      const indexB = categoryOrder.indexOf(b);
      if (indexA === -1 && indexB === -1) return a.localeCompare(b);
      if (indexA === -1) return 1;
      if (indexB === -1) return -1;
      return indexA - indexB;
    });

    return sortedCategories.map((category) => ({
      category,
      items: grouped[category],
    }));
  }, [items]);

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

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto no-scrollbar pb-32">
        {itemsByCategory.map(({ category, items: categoryItems }, idx) => (
          <div key={category}>
            <CategorySection
              category={category}
              items={categoryItems}
              onToggleItem={handleToggleItem}
              onSelectItem={handleSelectItem}
            />
            {idx < itemsByCategory.length - 1 && (
              <div className="h-px bg-border-light dark:bg-border-dark mx-5 mt-2" />
            )}
          </div>
        ))}

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
    </div>
  );
}
