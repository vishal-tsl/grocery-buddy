"use client";

import { useState } from "react";
import { GroceryItem as GroceryItemType, MatchSource } from "@/types";
import { urlImageProvider } from "@/lib/image";
import clsx from "clsx";
import { Icon } from "./Icon";
import { ItemFeedbackButton } from "./ItemFeedbackButton";

const MATCH_SOURCE_LABEL: Record<MatchSource, string> = {
  product: "Product",
  keyword: "Keyword",
  ai_text: "AI text",
};

function matchSourceChipClass(source: MatchSource): string {
  const base = "inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium";
  switch (source) {
    case "product":
      return clsx(base, "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400");
    case "keyword":
      return clsx(base, "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400");
    case "ai_text":
    default:
      return clsx(base, "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400");
  }
}

function confidenceChipClass(score: number): string {
  void score;
  const base = "inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium";
  return clsx(base, "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400");
}

interface GroceryItemProps {
  item: GroceryItemType;
  onToggle: (id: string) => void;
  onSelect: (item: GroceryItemType) => void;
}

export function GroceryItem({
  item,
  onToggle,
  onSelect,
}: GroceryItemProps) {
  const [imagePopupOpen, setImagePopupOpen] = useState(false);
  const [thumbError, setThumbError] = useState(false);

  const displayName = item.product_name;
  const isKeyword = item.match_source === "keyword";
  const showImageSlot = !isKeyword || Boolean(item.image_url);
  const itemImageUrl = urlImageProvider(item.image_url, "s");
  const hasImage = Boolean(itemImageUrl && !thumbError);
  const brand = isKeyword
    ? null
    : (
      item.brand ??
      (item.selected_option_index != null &&
      item.options &&
      item.options[item.selected_option_index - 1]?.brand
        ? item.options[item.selected_option_index - 1].brand
        : item.options?.[0]?.brand)
    );
  const brandLine = brand ? `${brand}` : null;

  const handleImageAreaClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!hasImage) return;
    setImagePopupOpen(true);
  };

  return (
    <div className="border-b border-gray-100 dark:border-gray-700">
      {/* Main Item Row */}
      <div
        className="flex items-start justify-between gap-3 px-5 py-3 hover:bg-surface-light dark:hover:bg-surface-dark transition cursor-pointer"
        onClick={() => onSelect(item)}
      >
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <input
            type="checkbox"
            checked={item.checked}
            onChange={() => onToggle(item.id)}
            className="custom-checkbox mt-1 flex-shrink-0"
            onClick={(e) => e.stopPropagation()}
          />
          <div className="flex flex-col flex-1 min-w-0">
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
            {brandLine && !item.checked && (
              <span className="text-sm text-gray-500 dark:text-gray-400 mt-0.5 block">
                {brandLine}
              </span>
            )}
            {/* Quick action pills */}
            {!item.checked && item.notes && (
              <p
                className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-3 break-words font-serif"
                title={item.notes}
              >
                <span className="text-gray-500 dark:text-gray-500" aria-hidden>
                  &ldquo;
                </span>
                {item.notes}
                <span className="text-gray-500 dark:text-gray-500" aria-hidden>
                  &rdquo;
                </span>
              </p>
            )}
            {!item.checked && item.quantity != null && (
              <div className="flex flex-wrap gap-2 mt-1">
                <span
                  className={clsx(
                    "px-2 py-0.5 rounded text-[10px] font-medium",
                    item.quantity !== 1
                      ? "bg-violet-100 text-violet-900 dark:bg-violet-900/40 dark:text-violet-200"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                  )}
                >
                  Qty: {item.quantity}
                </span>
              </div>
            )}
            {/* Product/Keyword + Confidence + Selected option index */}
            {(item.match_source || typeof item.confidence === "number" || (item.selected_suggestion_index != null && item.total_suggestions != null) || (item.selected_option_index != null && (item.options?.length ?? 0) > 0) || (item.autocomplete_query != null && item.autocomplete_query !== "")) && (
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {item.match_source && (
                  <span className={matchSourceChipClass(item.match_source)}>
                    {MATCH_SOURCE_LABEL[item.match_source]}
                  </span>
                )}
                {typeof item.confidence === "number" && (
                  <span className={confidenceChipClass(item.confidence)}>
                    {item.confidence.toFixed(2)}
                  </span>
                )}
                {item.autocomplete_query != null && item.autocomplete_query !== "" && (
                  <span
                    className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                    title="Phrase sent to autocomplete"
                  >
                    {item.autocomplete_query}
                  </span>
                )}
                {(item.selected_suggestion_index != null && item.total_suggestions != null
                  ? (
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400"
                        title="Auto-selected suggestion among API results"
                      >
                        Option {item.selected_suggestion_index} of {item.total_suggestions}
                      </span>
                    )
                  : item.match_source !== "keyword" && item.selected_option_index != null && item.options && item.options.length > 0 && (
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400"
                        title="Auto-selected option from list"
                      >
                        Option {item.selected_option_index} of {item.options.length}
                      </span>
                    )
                )}
              </div>
            )}
          </div>
        </div>

        {/* Feedback button + Image on the right */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div onClick={(e) => e.stopPropagation()}>
            <ItemFeedbackButton item={item} />
          </div>
          {showImageSlot &&
            (hasImage ? (
              <button
                type="button"
                className={clsx(
                  "w-11 h-11 rounded-lg border border-border-light dark:border-border-dark flex-shrink-0 flex items-center justify-center overflow-hidden bg-white",
                  item.checked && "opacity-50 grayscale"
                )}
                onClick={handleImageAreaClick}
                aria-label="View image"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={itemImageUrl!}
                  alt={item.product_name}
                  className="w-full h-full object-contain"
                  referrerPolicy="no-referrer"
                  onError={() => setThumbError(true)}
                />
              </button>
            ) : (
              <div
                className="w-11 h-11 flex-shrink-0 rounded-lg border border-transparent"
                aria-hidden
              />
            ))}
        </div>
      </div>

      {/* Image popup – big view or simple no-image placeholder */}
      {imagePopupOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/60 z-50"
            onClick={() => setImagePopupOpen(false)}
            aria-hidden
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
            <div
              className="pointer-events-auto bg-white dark:bg-gray-900 rounded-2xl shadow-xl max-w-sm w-full max-h-[85vh] flex flex-col overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-end p-2">
                <button
                  type="button"
                  onClick={() => setImagePopupOpen(false)}
                  className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                  aria-label="Close"
                >
                  <Icon name="close" size={24} className="text-gray-600 dark:text-gray-400" />
                </button>
              </div>
              <div className="flex-1 flex flex-col items-center justify-center p-6 pb-8">
                {hasImage ? (
                  <>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={urlImageProvider(item.image_url, "l") ?? itemImageUrl!}
                      alt={item.product_name}
                      className="max-w-full max-h-[70vh] w-auto h-auto object-contain rounded-lg"
                      referrerPolicy="no-referrer"
                    />
                    <p className="mt-3 text-sm font-medium text-gray-700 dark:text-gray-300 text-center">
                      {item.product_name}
                    </p>
                  </>
                ) : (
                  <>
                    <div className="w-16 h-16 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center mb-4">
                      <Icon name="image" size={32} className="text-gray-500 dark:text-gray-400" />
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
