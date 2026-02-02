"use client";

import { GroceryList } from "@/types";
import Link from "next/link";

interface ListCardProps {
  list: GroceryList;
  isActive?: boolean;
}

export function ListCard({ list, isActive = false }: ListCardProps) {
  const progress = Math.round((list.completed_items / list.total_items) * 100);

  if (isActive) {
    return (
      <div className="group relative flex flex-col gap-4 rounded-2xl bg-surface-light dark:bg-surface-dark p-5 shadow-soft dark:shadow-none border border-transparent dark:border-white/5 transition-transform active:scale-[0.99] duration-200">
        <div className="flex justify-between items-start">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-accent-green-100 text-accent-green-800 dark:bg-accent-green-900/40 dark:text-accent-green-400">
                Active
              </span>
            </div>
            <h3 className="text-xl font-bold text-text-main dark:text-white leading-tight">
              {list.name}
            </h3>
            <p className="text-text-sub dark:text-accent-green-400/80 text-sm font-medium">
              {list.completed_items}/{list.total_items} items bought
            </p>
          </div>
          <Link
            href={`/list/${list.id}`}
            className="flex h-9 px-4 items-center justify-center rounded-lg bg-primary hover:bg-primary-hover text-white text-sm font-bold transition-colors"
          >
            Continue
          </Link>
        </div>

        <div className="flex flex-col gap-2">
          <div className="w-full rounded-full bg-gray-100 dark:bg-gray-700/50 h-2.5 overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="flex gap-3 pt-1">
          {list.items.slice(0, 3).map((item, idx) =>
            item.image_url && item.image_url.startsWith("http") ? (
              <div
                key={idx}
                className="w-16 h-16 rounded-xl bg-gray-100 dark:bg-gray-800 bg-center bg-cover shadow-inner overflow-hidden"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={item.image_url}
                  alt={item.product_name}
                  className="w-full h-full object-cover"
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              </div>
            ) : (
              <div
                key={idx}
                className="w-16 h-16 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400 text-xs font-semibold"
              >
                {item.product_name.charAt(0).toUpperCase()}
              </div>
            )
          )}
          {list.items.length > 3 && (
            <div className="w-16 h-16 rounded-xl bg-gray-50 dark:bg-gray-800/50 flex items-center justify-center border-2 border-dashed border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500 text-xs font-bold">
              +{list.items.length - 3}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <Link
      href={`/list/${list.id}`}
      className="flex items-center justify-between p-4 bg-surface-light dark:bg-surface-dark rounded-xl shadow-soft border border-transparent dark:border-white/5 active:bg-gray-50 dark:active:bg-white/5 transition-colors cursor-pointer"
    >
      <div className="flex items-center gap-4">
        <div className="flex items-center justify-center rounded-xl bg-accent-green-50 dark:bg-accent-green-900/20 shrink-0 w-12 h-12 text-accent-green-700 dark:text-accent-green-400">
          <span className="material-symbols-outlined">format_list_bulleted</span>
        </div>
        <div className="flex flex-col justify-center">
          <p className="text-text-main dark:text-white text-base font-semibold leading-normal">
            {list.name}
          </p>
          <p className="text-text-sub dark:text-accent-green-400/60 text-sm font-normal leading-normal">
            {list.date} • {list.total_items} items
          </p>
        </div>
      </div>
      <span className="material-symbols-outlined text-gray-400 dark:text-gray-600">
        chevron_right
      </span>
    </Link>
  );
}
