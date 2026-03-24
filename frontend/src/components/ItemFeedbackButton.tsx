"use client";

import { useState } from "react";
import { Icon } from "./Icon";
import { submitFeedback } from "@/lib/api";
import { GroceryItem } from "@/types";
import clsx from "clsx";

interface ItemFeedbackButtonProps {
  item: GroceryItem;
  onSubmitted?: () => void;
}

export function ItemFeedbackButton({ item, onSubmitted }: ItemFeedbackButtonProps) {
  const [popupOpen, setPopupOpen] = useState(false);
  const [positive, setPositive] = useState<boolean | null>(null);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (positive === null) return;
    setIsSubmitting(true);
    try {
      await submitFeedback({
        type: "item",
        positive,
        comment: comment.trim() || undefined,
        item_id: item.id,
        product_name: item.product_name,
        sku: item.sku ?? undefined,
        match_source: item.match_source,
      });
      setSubmitted(true);
      setPopupOpen(false);
      onSubmitted?.();
    } catch (err) {
      console.error("Feedback submit failed:", err);
      setIsSubmitting(false);
    }
  };

  const handleOpen = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!submitted) setPopupOpen(true);
  };

  const handleClose = (e: React.MouseEvent) => {
    e?.stopPropagation();
    setPopupOpen(false);
  };

  if (submitted) {
    return (
      <button
        type="button"
        onClick={(e) => e.stopPropagation()}
        className="p-1.5 rounded-lg text-accent-green-600 dark:text-accent-green-400"
        aria-label="Feedback submitted"
      >
        <Icon name="check_circle" size={18} />
      </button>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={handleOpen}
        className="p-1.5 rounded-lg text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
        aria-label="Send feedback"
      >
        <Icon name="thumb_up" size={18} />
      </button>

      {/* Feedback popup */}
      {popupOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/60 z-50"
            onClick={handleClose}
            aria-hidden
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
            <div
              className="pointer-events-auto w-full max-w-sm bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-5"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-semibold text-gray-800 dark:text-gray-200">
                  Rate this result
                </h3>
                <button
                  type="button"
                  onClick={handleClose}
                  className="p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400"
                  aria-label="Close"
                >
                  <Icon name="close" size={20} />
                </button>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 truncate" title={item.product_name}>
                {item.product_name}
              </p>
              <div className="flex gap-2 mb-4">
                <button
                  type="button"
                  onClick={() => setPositive(true)}
                  className={clsx(
                    "flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl transition font-medium",
                    positive === true
                      ? "bg-accent-green-100 dark:bg-accent-green-900/30 text-accent-green-700 dark:text-accent-green-400"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                  )}
                  aria-label="Thumbs up"
                >
                  <Icon name="thumb_up" size={22} filled={positive === true} />
                  Good
                </button>
                <button
                  type="button"
                  onClick={() => setPositive(false)}
                  className={clsx(
                    "flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl transition font-medium",
                    positive === false
                      ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                  )}
                  aria-label="Thumbs down"
                >
                  <Icon name="thumb_down" size={22} filled={positive === false} />
                  Wrong
                </button>
              </div>
              <input
                type="text"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a comment (optional)"
                className="w-full px-3 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50 mb-4"
                onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              />
              <button
                type="button"
                onClick={(e) => handleSubmit(e)}
                disabled={positive === null || isSubmitting}
                className="w-full py-2.5 text-sm font-medium rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
              >
                {isSubmitting ? "Sending..." : "Send feedback"}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
