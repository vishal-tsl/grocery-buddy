"use client";

import { useState } from "react";
import { Icon } from "./Icon";
import { submitFeedback } from "@/lib/api";
import clsx from "clsx";

interface WholeFeedbackBannerProps {
  rawInput: string;
  itemCount: number;
  onDismiss: () => void;
}

export function WholeFeedbackBanner({
  rawInput,
  itemCount,
  onDismiss,
}: WholeFeedbackBannerProps) {
  const [positive, setPositive] = useState<boolean | null>(null);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (positive === null) return;
    setIsSubmitting(true);
    try {
      await submitFeedback({
        type: "batch",
        positive,
        comment: comment.trim() || undefined,
        raw_input: rawInput,
        item_count: itemCount,
      });
      setSubmitted(true);
      setTimeout(onDismiss, 800);
    } catch (err) {
      console.error("Feedback submit failed:", err);
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="mx-4 mb-3 px-4 py-3 rounded-xl bg-accent-green-100 dark:bg-accent-green-900/30 border border-accent-green-200 dark:border-accent-green-800 text-accent-green-800 dark:text-accent-green-200 text-sm font-medium flex items-center gap-2">
        <Icon name="check_circle" size={20} className="text-accent-green-600 dark:text-accent-green-400" />
        Thanks for your feedback!
      </div>
    );
  }

  return (
    <div className="mx-4 mb-3 px-4 py-3 rounded-xl bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark shadow-soft">
      <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-3">
        How did we do overall?
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1">
          <button
            type="button"
            onClick={async () => {
              if (isSubmitting || submitted) return;
              setPositive(true);
              setIsSubmitting(true);
              try {
                await submitFeedback({
                  type: "batch",
                  positive: true,
                  comment: comment.trim() || undefined,
                  raw_input: rawInput,
                  item_count: itemCount,
                });
                setSubmitted(true);
                setTimeout(onDismiss, 800);
              } catch (err) {
                console.error("Feedback submit failed:", err);
                setPositive(null);
              } finally {
                setIsSubmitting(false);
              }
            }}
            disabled={isSubmitting || submitted}
            className={clsx(
              "p-2 rounded-lg transition",
              positive === true
                ? "bg-accent-green-100 dark:bg-accent-green-900/30 text-accent-green-700 dark:text-accent-green-400"
                : "bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
            )}
            aria-label="Thumbs up"
          >
            <Icon name="thumb_up" size={22} filled={positive === true} />
          </button>
          <button
            type="button"
            onClick={() => setPositive(false)}
            className={clsx(
              "p-2 rounded-lg transition",
              positive === false
                ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                : "bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
            )}
            aria-label="Thumbs down"
          >
            <Icon name="thumb_down" size={22} filled={positive === false} />
          </button>
        </div>
        <input
          type="text"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Add a comment (optional)"
          className="flex-1 min-w-[140px] px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50"
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={positive === null || isSubmitting}
          className="px-3 py-2 text-sm font-medium rounded-lg bg-primary hover:bg-primary-hover disabled:bg-gray-300 disabled:dark:bg-gray-700 disabled:cursor-not-allowed text-white transition-colors"
        >
          {isSubmitting ? "..." : "Submit"}
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
          aria-label="Dismiss"
        >
          <Icon name="close" size={20} />
        </button>
      </div>
    </div>
  );
}
