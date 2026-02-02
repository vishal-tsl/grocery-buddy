"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GroceryItem as GroceryItemType, ProductOption } from "@/types";
import { Icon } from "./Icon";
import clsx from "clsx";

interface GroceryItemProps {
  item: GroceryItemType;
  onToggle: (id: string) => void;
  onSelect: (item: GroceryItemType) => void;
  onSpecify?: (item: GroceryItemType) => void;
  onSelectBrand?: (item: GroceryItemType, option: ProductOption) => void;
}

export function GroceryItem({ 
  item, 
  onToggle, 
  onSelect, 
  onSpecify,
  onSelectBrand 
}: GroceryItemProps) {
  const [showInlineOptions, setShowInlineOptions] = useState(false);
  
  const displayName = item.product_name;
  const hasOptions = item.options && item.options.length > 0;
  const needsSpec = item.needs_specification && hasOptions;

  const handleSpecifyClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onSpecify) {
      onSpecify(item);
    } else {
      setShowInlineOptions(!showInlineOptions);
    }
  };

  const handleBrandSelect = (option: ProductOption) => {
    if (onSelectBrand) {
      onSelectBrand(item, option);
    }
    setShowInlineOptions(false);
  };

  const handleCloseInline = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowInlineOptions(false);
  };

  return (
    <div className="border-b border-gray-100 dark:border-gray-700">
      {/* Main Item Row */}
      <div
        className="flex items-start justify-between px-5 py-3 hover:bg-surface-light dark:hover:bg-surface-dark transition cursor-pointer"
        onClick={() => onSelect(item)}
      >
        <div className="flex items-start gap-4 flex-1">
          <input
            type="checkbox"
            checked={item.checked}
            onChange={() => onToggle(item.id)}
            className="custom-checkbox mt-1"
            onClick={(e) => e.stopPropagation()}
          />
          <div className="flex flex-col flex-1">
            <span
              className={clsx(
                "text-lg transition-colors",
                item.checked
                  ? "text-gray-400 dark:text-gray-500 line-through decoration-gray-400 dark:decoration-gray-500"
                  : "text-gray-800 dark:text-gray-200"
              )}
            >
              {displayName}
            </span>
            {/* Quick action pills */}
            {!item.checked && (item.notes || item.quantity || needsSpec) && (
              <div className="flex flex-wrap gap-2 mt-1">
                {item.notes && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                    Note
                  </span>
                )}
                {item.quantity && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                    Qty: {item.quantity}
                  </span>
                )}
                {needsSpec && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                    Specify
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
        
        {/* Right side: Specify button or Image */}
        {!item.checked && needsSpec ? (
          <button
            onClick={handleSpecifyClick}
            className="text-primary font-medium text-sm hover:underline"
          >
            Specify
          </button>
        ) : item.image_url && item.image_url.startsWith("http") ? (
          <div className={clsx(
            "w-10 h-10 rounded-md overflow-hidden border border-border-light dark:border-border-dark bg-white flex-shrink-0",
            item.checked && "opacity-50 grayscale"
          )}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={item.image_url}
              alt={item.product_name}
              className="w-full h-full object-contain"
              onError={(e) => { e.currentTarget.parentElement!.style.display = 'none'; }}
            />
          </div>
        ) : null}
      </div>

      {/* Inline Brand Options */}
      <AnimatePresence>
        {showInlineOptions && hasOptions && !item.checked && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="ml-14 mr-5 mb-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-xl">
              {/* Header */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-primary font-semibold text-sm">Which one?</span>
                <button onClick={handleCloseInline} className="text-gray-400 hover:text-gray-600">
                  <Icon name="close" size={18} />
                </button>
              </div>
              
              {/* Brand Pills - Horizontal Scroll */}
              <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
                {item.options?.slice(0, 5).map((option, idx) => (
                  <button
                    key={option.sku || idx}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleBrandSelect(option);
                    }}
                    className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-primary transition whitespace-nowrap flex-shrink-0"
                  >
                    {option.image_url && (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img
                        src={option.image_url}
                        alt={option.name}
                        className="w-6 h-6 object-contain rounded"
                        onError={(e) => { e.currentTarget.style.display = 'none'; }}
                      />
                    )}
                    <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">
                      {option.brand || option.name.split(' ')[0]}
                    </span>
                  </button>
                ))}
                
                {/* More button if there are more options */}
                {item.options && item.options.length > 5 && onSpecify && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSpecify(item);
                    }}
                    className="flex items-center gap-1 px-3 py-2 text-primary text-sm font-medium whitespace-nowrap"
                  >
                    More
                    <Icon name="chevron_right" size={16} />
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
