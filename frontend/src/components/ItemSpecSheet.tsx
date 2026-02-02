"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Icon } from "./Icon";
import { GroceryItem, ProductOption } from "@/types";

interface ItemSpecSheetProps {
  isOpen: boolean;
  item: GroceryItem | null;
  onClose: () => void;
  onUpdate: (updatedItem: GroceryItem) => void;
}

export function ItemSpecSheet({
  isOpen,
  item,
  onClose,
  onUpdate,
}: ItemSpecSheetProps) {
  const [quantity, setQuantity] = useState<number>(item?.quantity || 1);
  const [notes, setNotes] = useState<string>(item?.notes || "");
  const [selectedOption, setSelectedOption] = useState<ProductOption | null>(null);

  if (!item) return null;

  const handleSelectOption = (option: ProductOption) => {
    setSelectedOption(option);
    onUpdate({
      ...item,
      product_name: option.name,
      sku: option.sku,
      brand: option.brand,
      image_url: option.image_url || item.image_url,
      needs_specification: false,
    });
  };

  const handleUpdateQuantity = (newQty: number) => {
    setQuantity(newQty);
    onUpdate({
      ...item,
      quantity: newQty,
    });
  };

  const handleUpdateNotes = () => {
    onUpdate({
      ...item,
      notes: notes,
    });
  };

  const hasOptions = item.options && item.options.length > 1;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 dark:bg-black/50 z-40"
            onClick={onClose}
          />

          {/* Sheet */}
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed bottom-0 left-0 right-0 bg-surface-light dark:bg-surface-dark rounded-t-3xl shadow-sheet z-50 max-h-[70vh] flex flex-col"
          >
            {/* Handle */}
            <div className="flex justify-center pt-3 pb-2">
              <div className="w-10 h-1 rounded-full bg-gray-300 dark:bg-gray-600" />
            </div>

            {/* Header with Product Image */}
            <div className="flex items-start gap-4 px-6 pb-4 border-b border-gray-100 dark:border-gray-700">
              {/* Product Image */}
              {item.image_url && item.image_url.startsWith("http") ? (
                <div className="w-20 h-20 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 overflow-hidden flex-shrink-0">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={item.image_url}
                    alt={item.product_name}
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      // Hide broken image and show fallback
                      e.currentTarget.style.display = 'none';
                      e.currentTarget.nextElementSibling?.classList.remove('hidden');
                    }}
                  />
                  <div className="hidden w-full h-full flex items-center justify-center">
                    <Icon name="image" size={32} className="text-gray-300" />
                  </div>
                </div>
              ) : (
                <div className="w-20 h-20 rounded-xl bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 flex items-center justify-center flex-shrink-0">
                  <Icon name="shopping_basket" size={32} className="text-gray-400" />
                </div>
              )}
              
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  {item.category || "Item"}
                </p>
                <h2 className="text-xl font-bold text-gray-800 dark:text-white truncate">
                  {item.product_name}
                </h2>
                {item.brand && (
                  <p className="text-sm text-primary font-medium">{item.brand}</p>
                )}
                {item.size && (
                  <p className="text-sm text-gray-500 dark:text-gray-400">{item.size}</p>
                )}
              </div>
              
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 dark:bg-gray-700 flex-shrink-0"
              >
                <Icon name="close" size={18} className="text-gray-500" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Quick Actions */}
              <div className="flex gap-2">
                <button
                  onClick={() => setNotes(notes ? "" : "Add note...")}
                  className="px-4 py-2 rounded-full border border-gray-200 dark:border-gray-600 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
                >
                  Note
                </button>
                <button className="px-4 py-2 rounded-full border border-gray-200 dark:border-gray-600 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition flex items-center gap-2">
                  Qty: {quantity}
                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleUpdateQuantity(Math.max(1, quantity - 1));
                      }}
                      className="w-5 h-5 rounded-full bg-gray-200 dark:bg-gray-600 text-xs font-bold"
                    >
                      -
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleUpdateQuantity(quantity + 1);
                      }}
                      className="w-5 h-5 rounded-full bg-gray-200 dark:bg-gray-600 text-xs font-bold"
                    >
                      +
                    </button>
                  </div>
                </button>
                {item.needs_specification && (
                  <span className="px-4 py-2 rounded-full bg-amber-100 dark:bg-amber-900/30 text-sm font-medium text-amber-700 dark:text-amber-400">
                    Specify
                  </span>
                )}
              </div>

              {/* Product Options */}
              {hasOptions && item.needs_specification && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-primary font-semibold">Which one?</p>
                    <button className="text-gray-400 hover:text-gray-600">
                      <Icon name="close" size={18} />
                    </button>
                  </div>
                  <div className="flex gap-2 overflow-x-auto pb-2 -mx-2 px-2">
                    {item.options?.map((option) => (
                      <button
                        key={option.sku}
                        onClick={() => handleSelectOption(option)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl border-2 transition whitespace-nowrap ${
                          selectedOption?.sku === option.sku
                            ? "border-primary bg-primary/10"
                            : "border-gray-200 dark:border-gray-600 hover:border-primary/50"
                        }`}
                      >
                        {option.image_url && option.image_url.startsWith("http") && (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img
                            src={option.image_url}
                            alt={option.name}
                            className="w-8 h-8 rounded object-cover bg-gray-100"
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                          />
                        )}
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          {option.brand ? option.name : option.name}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Notes Input */}
              {notes !== "" && (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Notes
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    onBlur={handleUpdateNotes}
                    placeholder="Add a note..."
                    className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 resize-none"
                    rows={2}
                  />
                </div>
              )}

              {/* Item Details */}
              <div className="space-y-3 pt-4 border-t border-gray-100 dark:border-gray-700">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Details
                </p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {item.brand && (
                    <div>
                      <span className="text-gray-500">Brand:</span>
                      <span className="ml-2 text-gray-800 dark:text-gray-200">
                        {item.brand}
                      </span>
                    </div>
                  )}
                  {item.size && (
                    <div>
                      <span className="text-gray-500">Size:</span>
                      <span className="ml-2 text-gray-800 dark:text-gray-200">
                        {item.size}
                      </span>
                    </div>
                  )}
                  {item.unit && (
                    <div>
                      <span className="text-gray-500">Unit:</span>
                      <span className="ml-2 text-gray-800 dark:text-gray-200">
                        {item.unit}
                      </span>
                    </div>
                  )}
                  {item.sku && (
                    <div>
                      <span className="text-gray-500">SKU:</span>
                      <span className="ml-2 text-gray-800 dark:text-gray-200">
                        {item.sku}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Done Button */}
            <div className="p-6 border-t border-gray-100 dark:border-gray-700 safe-bottom">
              <button
                onClick={onClose}
                className="w-full h-12 bg-primary hover:bg-primary-hover rounded-xl flex items-center justify-center text-white font-bold transition-colors"
              >
                Done
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
