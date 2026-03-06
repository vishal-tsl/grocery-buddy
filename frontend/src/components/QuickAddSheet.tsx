"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Icon } from "./Icon";
import { parseGroceryList } from "@/lib/api";
import { GroceryItem } from "@/types";

interface QuickAddSheetProps {
  isOpen: boolean;
  onClose: () => void;
  onAddItems: (items: GroceryItem[]) => void;
  listName: string;
}

export function QuickAddSheet({
  isOpen,
  onClose,
  onAddItems,
  listName,
}: QuickAddSheetProps) {
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [parsedItems, setParsedItems] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isOpen && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isOpen]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setInputText(text);

    // Live preview of items
    const lines = text
      .split(/[\n,]/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    setParsedItems(lines);
  };

  const handleSubmit = async () => {
    if (!inputText.trim() || isProcessing) return;

    setIsProcessing(true);
    try {
      const response = await parseGroceryList(inputText);
      const newItems: GroceryItem[] = response.items.map((item, idx) => ({
        id: `new-${Date.now()}-${idx}`,
        product_name: item.product_name,
        sku: item.sku,
        quantity: item.quantity,
        unit: item.unit,
        notes: item.notes,
        checked: false,
        category: item.category || undefined,
        image_url: item.image_url || undefined,
        brand: item.brand,
        size: item.size,
        needs_specification: item.needs_specification,
        options: item.options,
        match_source: item.match_source,
        match_reason: item.match_reason,
        confidence: item.confidence,
        selected_option_index: item.selected_option_index,
        selected_suggestion_index: item.selected_suggestion_index,
        total_suggestions: item.total_suggestions,
        autocomplete_query: item.autocomplete_query,
      }));

      onAddItems(newItems);
      setInputText("");
      setParsedItems([]);
      onClose();
    } catch (error) {
      console.error("Failed to parse items:", error);
      // Fallback: add items as-is
      const fallbackItems: GroceryItem[] = parsedItems.map((text, idx) => ({
        id: `new-${Date.now()}-${idx}`,
        product_name: text,
        sku: null,
        quantity: null,
        unit: null,
        notes: "",
        checked: false,
        match_source: "ai_text",
      }));
      onAddItems(fallbackItems);
      setInputText("");
      setParsedItems([]);
      onClose();
    } finally {
      setIsProcessing(false);
    }
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
            className="fixed inset-0 bg-black/20 dark:bg-black/50 z-40"
            onClick={onClose}
          />

          {/* Sheet */}
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed bottom-0 left-0 right-0 bg-surface-light dark:bg-surface-dark rounded-t-3xl shadow-sheet z-50 max-h-[85vh] flex flex-col"
          >
            {/* Handle */}
            <div className="flex justify-center pt-3 pb-2">
              <div className="w-10 h-1 rounded-full bg-gray-300 dark:bg-gray-600" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-6 pb-4">
              <h2 className="text-xl font-bold text-gray-800 dark:text-white">
                {listName}
              </h2>
              <button
                onClick={onClose}
                className="text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700"
              >
                Close
              </button>
            </div>

            {/* Input Area */}
            <div className="px-6 pb-4">
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  value={inputText}
                  onChange={handleInputChange}
                  placeholder="Type or paste your grocery items...&#10;e.g., Butter, Eggs, Bread&#10;Tomato Paste 8oz&#10;Milk 2%"
                  className="w-full h-32 p-4 bg-gray-50 dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="px-6 py-4 border-t border-gray-100 dark:border-gray-700 safe-bottom">
              <button
                onClick={handleSubmit}
                disabled={parsedItems.length === 0 || isProcessing}
                className="w-full h-12 bg-primary hover:bg-primary-hover disabled:bg-gray-300 disabled:dark:bg-gray-700 rounded-xl flex items-center justify-center gap-2 text-white font-bold transition-colors"
              >
                {isProcessing ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Icon name="add" size={20} />
                    Add Items
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
