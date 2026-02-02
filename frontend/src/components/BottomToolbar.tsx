"use client";

import { Icon } from "./Icon";

interface BottomToolbarProps {
  onQuickAdd: () => void;
}

export function BottomToolbar({ onQuickAdd }: BottomToolbarProps) {
  return (
    <div className="fixed bottom-6 left-0 right-0 px-6 flex items-end justify-between pointer-events-none z-30">
      <div className="max-w-md mx-auto w-full flex items-end justify-between">
        {/* Left Toolbar */}
        <div className="pointer-events-auto bg-surface-light dark:bg-surface-dark shadow-soft-lg rounded-full px-6 py-3 flex items-center gap-8 text-gray-700 dark:text-gray-300 border border-gray-100 dark:border-gray-700">
          <button className="flex items-center justify-center hover:text-gray-900 dark:hover:text-white transition">
            <Icon name="text_fields" size={24} />
          </button>
          <button className="flex items-center justify-center hover:text-gray-900 dark:hover:text-white transition">
            <Icon name="history" size={24} />
          </button>
          <button className="flex items-center justify-center hover:text-gray-900 dark:hover:text-white transition">
            <Icon name="format_align_justify" size={24} className="rotate-90" />
          </button>
        </div>

        {/* Quick Add FAB */}
        <button
          onClick={onQuickAdd}
          className="pointer-events-auto w-14 h-14 bg-surface-light dark:bg-surface-dark rounded-full shadow-soft-lg flex items-center justify-center text-gray-700 dark:text-gray-300 border border-gray-100 dark:border-gray-700 hover:scale-105 active:scale-95 transition"
        >
          <Icon name="edit_note" size={24} />
        </button>
      </div>
    </div>
  );
}
