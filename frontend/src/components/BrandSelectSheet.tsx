"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Icon } from "./Icon";
import { GroceryItem, ProductOption } from "@/types";

interface BrandSelectSheetProps {
  isOpen: boolean;
  item: GroceryItem | null;
  onClose: () => void;
  onSelectBrand: (item: GroceryItem, option: ProductOption) => void;
}

export function BrandSelectSheet({
  isOpen,
  item,
  onClose,
  onSelectBrand,
}: BrandSelectSheetProps) {
  const [searchQuery, setSearchQuery] = useState("");

  if (!item) return null;

  const options = item.options || [];
  
  // Filter options by search query
  const filteredOptions = searchQuery
    ? options.filter((opt) =>
        opt.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (opt.brand && opt.brand.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : options;

  const handleSelect = (option: ProductOption) => {
    onSelectBrand(item, option);
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 dark:bg-black/50 z-50"
            onClick={onClose}
          />

          {/* Full Screen Sheet */}
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed inset-x-0 top-12 bottom-0 bg-surface-light dark:bg-surface-dark rounded-t-3xl shadow-sheet z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700">
              <button
                onClick={onClose}
                className="w-10 h-10 flex items-center justify-center"
              >
                <Icon name="close" size={24} className="text-gray-600 dark:text-gray-400" />
              </button>
              <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
                {item.product_name}
              </h2>
              <div className="w-10" /> {/* Spacer for centering */}
            </div>

            {/* Brand Options List */}
            <div className="flex-1 overflow-y-auto">
              {filteredOptions.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                  <Icon name="search_off" size={48} />
                  <p className="mt-2">No brands found</p>
                </div>
              ) : (
                filteredOptions.map((option, idx) => (
                  <button
                    key={option.sku || idx}
                    onClick={() => handleSelect(option)}
                    className="w-full flex items-center gap-4 px-5 py-4 border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    {/* Product Image */}
                    <div className="w-24 h-24 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 overflow-hidden flex-shrink-0 flex items-center justify-center">
                      {option.image_url ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={option.image_url}
                          alt={option.name}
                          className="w-full h-full object-contain p-2"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none';
                            e.currentTarget.nextElementSibling?.classList.remove('hidden');
                          }}
                        />
                      ) : null}
                      <div className={option.image_url ? "hidden" : ""}>
                        <Icon name="inventory_2" size={32} className="text-gray-300" />
                      </div>
                    </div>

                    {/* Product Name */}
                    <span className="flex-1 text-left text-lg text-gray-800 dark:text-white font-medium">
                      {option.name}
                    </span>

                    {/* Arrow */}
                    <Icon name="chevron_right" size={24} className="text-gray-400" />
                  </button>
                ))
              )}
            </div>

            {/* Search Bar */}
            <div className="px-5 py-4 border-t border-gray-100 dark:border-gray-700 safe-bottom">
              <div className="relative">
                <Icon
                  name="search"
                  size={20}
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
                />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={`Search all ${item.product_name.toLowerCase()}`}
                  className="w-full h-12 pl-12 pr-4 bg-gray-100 dark:bg-gray-800 rounded-full text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
