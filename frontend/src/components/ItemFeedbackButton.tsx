"use client";

import { useState } from "react";
import { Icon } from "./Icon";
import { submitFeedback } from "@/lib/api";
import { GroceryItem } from "@/types";

interface ItemFeedbackButtonProps {
  item: GroceryItem;
  onSubmitted?: () => void;
}

export function ItemFeedbackButton({ item, onSubmitted }: ItemFeedbackButtonProps) {
  const [negativeModalOpen, setNegativeModalOpen] = useState(false);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [vote, setVote] = useState<"up" | "down" | null>(null);

  const thumbsUp = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (vote !== null) return;
    setVote("up");
    onSubmitted?.();
    try {
      await submitFeedback({
        type: "item",
        positive: true,
        item_id: item.id,
        product_name: item.product_name,
        sku: item.sku ?? undefined,
        match_source: item.match_source,
      });
    } catch (err) {
      console.error("Feedback submit failed:", err);
      setVote(null);
    }
  };

  const submitNegative = async (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setIsSubmitting(true);
    try {
      await submitFeedback({
        type: "item",
        positive: false,
        comment: comment.trim() || undefined,
        item_id: item.id,
        product_name: item.product_name,
        sku: item.sku ?? undefined,
        match_source: item.match_source,
      });
      setNegativeModalOpen(false);
      setVote("down");
      onSubmitted?.();
    } catch (err) {
      console.error("Feedback submit failed:", err);
      setIsSubmitting(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const openNegative = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (vote !== null) return;
    setNegativeModalOpen(true);
  };

  const handleCloseModal = (e: React.MouseEvent) => {
    e.stopPropagation();
    setNegativeModalOpen(false);
  };

  if (vote === "up") {
    return (
      <button
        type="button"
        onClick={(e) => e.stopPropagation()}
        className="p-1.5 rounded-lg text-accent-green-600 dark:text-accent-green-400"
        aria-label="Positive feedback saved"
      >
        <Icon name="check_circle" size={18} />
      </button>
    );
  }

  if (vote === "down") {
    return (
      <span
        className="p-1.5 rounded-lg text-red-600 dark:text-red-400 inline-flex"
        aria-label="Negative feedback saved"
        title="Negative feedback"
      >
        <span className="text-lg leading-none font-bold" aria-hidden>
          ❌
        </span>
      </span>
    );
  }

  return (
    <>
      <div className="flex items-center gap-0.5" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          onClick={thumbsUp}
          className="p-1.5 rounded-lg text-gray-400 dark:text-gray-500 hover:text-accent-green-600 dark:hover:text-accent-green-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          aria-label="Thumbs up — good match"
        >
          <Icon name="thumb_up" size={18} />
        </button>
        <button
          type="button"
          onClick={openNegative}
          disabled={isSubmitting}
          className="p-1.5 rounded-lg text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition disabled:opacity-50"
          aria-label="Thumbs down — report issue"
        >
          <Icon name="thumb_down" size={18} />
        </button>
      </div>

      {negativeModalOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/60 z-50"
            onClick={handleCloseModal}
            aria-hidden
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
            <div
              className="pointer-events-auto w-full max-w-sm bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-5"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-semibold text-gray-800 dark:text-gray-200">
                  What went wrong?
                </h3>
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400"
                  aria-label="Close"
                >
                  <Icon name="close" size={20} />
                </button>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 truncate" title={item.product_name}>
                {item.product_name}
              </p>
              <input
                type="text"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a comment (optional)"
                className="w-full px-3 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50 mb-4"
                onKeyDown={(e) => e.key === "Enter" && submitNegative()}
              />
              <button
                type="button"
                onClick={(e) => submitNegative(e)}
                disabled={isSubmitting}
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
