"use client";

import { useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";

export default function RecipePage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-background-light dark:bg-background-dark flex justify-center">
      <div className="w-full max-w-md bg-white dark:bg-gray-900 min-h-screen relative shadow-xl flex flex-col">
        <header className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800">
          <button
            onClick={() => router.back()}
            className="p-2 -ml-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          >
            <Icon name="arrow_back" size={24} className="text-gray-600 dark:text-gray-300" />
          </button>
          <h1 className="text-lg font-semibold text-gray-800 dark:text-white">
            Recipe to List
          </h1>
          <div className="w-10" />
        </header>

        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center gap-3">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-2xl flex items-center justify-center">
            <Icon name="pause_circle" size={32} className="text-gray-400" />
          </div>
          <h2 className="text-xl font-bold text-gray-800 dark:text-white">
            Recipe Module Disabled
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            This feature is temporarily turned off. Enable it from the backend when ready.
          </p>
        </div>
      </div>
    </div>
  );
}
