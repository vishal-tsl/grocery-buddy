"use client";

import { Icon } from "./Icon";

export function StatusBar() {
  const now = new Date();
  const time = now.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: false,
  });

  return (
    <div className="h-12 w-full flex items-end justify-between px-6 pb-2 text-xs font-semibold text-gray-900 dark:text-white">
      <span>{time}</span>
      <div className="flex items-center gap-1">
        <Icon name="signal_cellular_alt" size={14} />
        <Icon name="wifi" size={14} />
        <Icon name="battery_full" size={14} className="rotate-90" />
      </div>
    </div>
  );
}
