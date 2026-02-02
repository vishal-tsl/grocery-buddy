"use client";

import { useState } from "react";
import { Icon } from "@/components/Icon";
import { ListCard } from "@/components/ListCard";
import { GroceryList } from "@/types";
import Link from "next/link";

// Mock data for demonstration
const mockLists: GroceryList[] = [
  {
    id: "1",
    name: "Groceries, Feb 2",
    date: "Feb 2",
    total_items: 20,
    completed_items: 12,
    items: [
      {
        id: "1",
        product_name: "Mushrooms",
        sku: null,
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
        product_name: "Milk",
        sku: null,
        quantity: 1,
        unit: "gallon",
        notes: "",
        checked: false,
        category: "Dairy & Eggs",
        image_url:
          "https://lh3.googleusercontent.com/aida-public/AB6AXuCQb9IVGciXeKq5z5Ci5Iu0UaUoxwxM0PeEEhuAluWSmvlOYxVujgBsf8W6RRqALB1yJ-yk9qHh5wbeOZDqzb_fSFFX-P6Ehe_rhddHH3iZkGjQzXV3ZW-dv7qmnPH6yRJfOHWjjs0n4lJQqS501VKQaTuKa0124pK8UeeKPKsuAGxqdL4O215EKNsh_nKTGv8Zroh2WU2likdt0I5U00yCaC_j1H8MQqF5z5QAV2j3WnIj45Fwq9ufZWSdRlOky-jZFNGeALJVqoon",
      },
      {
        id: "3",
        product_name: "Apples",
        sku: null,
        quantity: 6,
        unit: null,
        notes: "",
        checked: false,
        category: "Fresh Produce",
        image_url:
          "https://lh3.googleusercontent.com/aida-public/AB6AXuCvhjSBxX7FHc_L8utUBc_9xz2hbf0bRvCTbKZ8UldY666pz2K4M8JIfTPytQUyFY_0GVzAnQVaZmgNPrzxydL6eVziAEM9riwOsos2E7snLaCy7Q7cs2hzhl52bDtJfeabq2erJ1kKVHshMnoXWL6QK_vpe-a-IJDU3ZFCgy7cG4cRMwHjpIdX_xqIpM2M-qZ4h3fzXTcfyZ34EJeTgvS-sPsrbHg7tmUc4P0B66EF9Vw_sUcS3oH797LLK2w9AZ3I76zK2Q3baGW7",
      },
    ],
  },
  {
    id: "2",
    name: "Weekly Essentials",
    date: "Jan 21",
    total_items: 15,
    completed_items: 15,
    items: [],
  },
  {
    id: "3",
    name: "Party Prep",
    date: "Jan 15",
    total_items: 8,
    completed_items: 8,
    items: [],
  },
];

export default function HomePage() {
  const [lists] = useState<GroceryList[]>(mockLists);
  const activeList = lists.find((l) => l.completed_items < l.total_items);
  const recentLists = lists.filter((l) => l.id !== activeList?.id);

  return (
    <div className="flex flex-col min-h-screen bg-background-light dark:bg-background-dark">
      {/* Header */}
      <header className="flex items-center px-5 pt-6 pb-2 justify-between sticky top-0 z-20 bg-background-light dark:bg-background-dark">
        <h2 className="text-2xl font-bold leading-tight tracking-tight flex-1">
          My Lists
        </h2>
        <button className="flex items-center justify-center w-10 h-10 rounded-full bg-surface-light dark:bg-surface-dark shadow-soft hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
          <Icon name="account_circle" size={24} />
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col gap-6 px-5 pt-4 pb-32">
        {/* Active List Section */}
        {activeList && (
          <section>
            <ListCard list={activeList} isActive />
          </section>
        )}

        {/* Recent Lists Section */}
        {recentLists.length > 0 && (
          <section className="flex flex-col gap-3">
            <h3 className="text-lg font-bold px-1">Recent Lists</h3>
            <div className="flex flex-col gap-3">
              {recentLists.map((list) => (
                <ListCard key={list.id} list={list} />
              ))}
            </div>
          </section>
        )}
      </main>

      {/* Fixed Bottom Button */}
      <div className="fixed bottom-0 left-0 right-0 p-5 bg-gradient-to-t from-background-light via-background-light to-transparent dark:from-background-dark dark:via-background-dark pt-12 pb-8 z-30 flex justify-center">
        <div className="w-full max-w-md">
          <Link
            href="/list/new"
            className="w-full h-14 bg-primary hover:bg-primary-hover active:scale-[0.98] transition-all rounded-2xl flex items-center justify-center gap-2 shadow-lg shadow-primary/25 text-white font-bold text-lg"
          >
            <Icon name="add" size={24} />
            Create New List
          </Link>
        </div>
      </div>
    </div>
  );
}
