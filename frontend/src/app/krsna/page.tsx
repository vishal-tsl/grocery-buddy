"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  adminEvents,
  adminMetrics,
  adminPurge,
  getAdminToken,
  type AdminEvent,
  type AdminMetrics,
} from "@/lib/api";
import { GroceryItem } from "@/components/GroceryItem";
import { GroceryItem as GroceryItemType } from "@/types";

export default function KrsnaDashboardPage() {
  const router = useRouter();
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [events, setEvents] = useState<AdminEvent[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [error, setError] = useState("");
  const [days, setDays] = useState(7);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [country, setCountry] = useState("");
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<AdminEvent | null>(null);
  const [purgeLoading, setPurgeLoading] = useState(false);
  const [copyStatus, setCopyStatus] = useState<{[key: string]: boolean}>({});

  const loadMetrics = useCallback(async () => {
    try {
      const data = await adminMetrics(days);
      setMetrics(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load metrics");
    }
  }, [days]);

  const loadEvents = useCallback(async () => {
    setEventsLoading(true);
    try {
      const res = await adminEvents({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        country: country || undefined,
        status: status || undefined,
        q: q || undefined,
        limit: 100,
        offset: 0,
      });
      setEvents(res.data);
      setCount(res.count);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load events");
    } finally {
      setEventsLoading(false);
    }
  }, [dateFrom, dateTo, country, status, q]);

  useEffect(() => {
    const token = getAdminToken();
    if (!token) {
      router.push("/krsna/login");
      return;
    }
    setLoading(true);
    setError("");
    Promise.all([
      loadMetrics(),
      loadEvents(),
    ]).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  useEffect(() => {
    if (!loading && getAdminToken()) {
      adminMetrics(days).then(setMetrics).catch(() => {});
    }
  }, [days, loading]);

  function handleLogout() {
    if (typeof window !== "undefined") localStorage.removeItem("admin_token");
    router.push("/krsna/login");
    router.refresh();
  }

  async function handlePurge() {
    setPurgeLoading(true);
    try {
      const res = await adminPurge();
      alert(`Purged ${res.deleted} old events.`);
      loadMetrics();
      loadEvents();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Purge failed");
    } finally {
      setPurgeLoading(false);
    }
  }

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus(prev => ({ ...prev, [id]: true }));
      setTimeout(() => {
        setCopyStatus(prev => ({ ...prev, [id]: false }));
      }, 2000);
    } catch (err) {
      console.error("Failed to copy: ", err);
    }
  };

  if (loading && !metrics) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950 text-slate-300">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-400 rounded-full animate-spin" />
          <p className="text-sm">Loading dashboard…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-slate-950 text-slate-100 overflow-hidden">
      {/* Header */}
      <header className="shrink-0 flex items-center justify-between gap-4 px-6 py-4 border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="flex items-center gap-6 min-w-0">
          <Link
            href="/"
            className="shrink-0 text-sm text-slate-400 hover:text-white transition-colors"
          >
            ← App
          </Link>
          <h1 className="text-xl font-semibold text-white truncate">
            Admin – Usage
          </h1>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={handlePurge}
            disabled={purgeLoading}
            className="px-4 py-2 rounded-lg text-sm font-medium border border-amber-500/50 text-amber-400 hover:bg-amber-500/10 disabled:opacity-50 transition-colors"
          >
            {purgeLoading ? "Purging…" : "Purge old"}
          </button>
          <button
            type="button"
            onClick={handleLogout}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-slate-700 text-slate-200 hover:bg-slate-600 transition-colors"
          >
            Log out
          </button>
        </div>
      </header>

      {/* Main content - scrollable */}
      <main className="flex-1 min-h-0 overflow-auto">
        <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {/* Metrics */}
          {metrics && (
            <section className="space-y-3">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
                  Metrics (last N days)
                </h2>
                <div className="flex gap-2">
                  {[7, 14, 30].map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setDays(d)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        days === d
                          ? "bg-emerald-600 text-white"
                          : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                      }`}
                    >
                      {d}d
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-4">
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Requests</p>
                  <p className="mt-1 text-2xl font-bold text-white tabular-nums">{metrics.total_requests}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Unique IPs</p>
                  <p className="mt-1 text-2xl font-bold text-white tabular-nums">{metrics.unique_ips}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Errors</p>
                  <p className="mt-1 text-2xl font-bold text-white tabular-nums">
                    {metrics.error_count} <span className="text-slate-500 font-normal">({(metrics.error_rate * 100).toFixed(2)}%)</span>
                  </p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Avg latency</p>
                  <p className="mt-1 text-2xl font-bold text-white tabular-nums">
                    {metrics.avg_latency_ms != null ? `${(metrics.avg_latency_ms / 1000).toFixed(2)}s` : "—"}
                  </p>
                </div>
                {Object.keys(metrics.by_country).length > 0 && (
                  <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 col-span-2 sm:col-span-4 lg:col-span-1">
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Top countries</p>
                    <p className="mt-1 text-sm text-slate-300 leading-relaxed">
                      {Object.entries(metrics.by_country)
                        .map(([c, n]) => `${c}: ${n}`)
                        .join(", ")}
                    </p>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Events */}
          <section className="space-y-3 flex flex-col min-h-0">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
                Events (who, input, output, where)
              </h2>
              <p className="text-sm text-slate-500">Total: {count} events</p>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3 p-4 rounded-xl border border-slate-800 bg-slate-900/30">
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30 outline-none"
              />
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30 outline-none"
              />
              <input
                type="text"
                placeholder="Country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 w-28 placeholder:text-slate-500 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30 outline-none"
              />
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30 outline-none"
              >
                <option value="">All status</option>
                <option value="success">success</option>
                <option value="error">error</option>
              </select>
              <input
                type="text"
                placeholder="Search input (q)"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 flex-1 min-w-[160px] placeholder:text-slate-500 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30 outline-none"
              />
              <button
                type="button"
                onClick={() => loadEvents()}
                disabled={eventsLoading}
                className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-500 disabled:opacity-50 transition-colors"
              >
                {eventsLoading ? "Loading…" : "Apply"}
              </button>
            </div>

            {/* Table container - full height feel */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/30 overflow-hidden flex-1 min-h-[320px]">
              <div className="overflow-auto max-h-[calc(100vh-420px)]">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 z-10 bg-slate-800/95 text-slate-400">
                    <tr>
                      <th className="text-left py-3 px-4 font-medium w-14">#</th>
                      <th className="text-left py-3 px-4 font-medium whitespace-nowrap">Time</th>
                      <th className="text-left py-3 px-4 font-medium">IP / Location</th>
                      <th className="text-left py-3 px-4 font-medium min-w-[200px]">Input</th>
                      <th className="text-left py-3 px-4 font-medium w-24">Status</th>
                      <th className="text-left py-3 px-4 font-medium w-28">Latency</th>
                      <th className="text-left py-3 px-4 font-medium w-20">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((ev, idx) => (
                      <tr
                        key={ev.id}
                        className="border-t border-slate-800/80 hover:bg-slate-800/40 transition-colors"
                      >
                        <td className="py-3 px-4 text-slate-500 tabular-nums">{ev.id}</td>
                        <td className="py-3 px-4 whitespace-nowrap text-slate-400">
                          {ev.created_at ? new Date(ev.created_at).toLocaleString() : "—"}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-mono text-xs text-slate-300">{ev.client_ip || "—"}</span>
                          {(ev.country || ev.city) && (
                            <span className="ml-1 text-slate-500 text-xs">
                              ({[ev.city, ev.region, ev.country].filter(Boolean).join(", ")})
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 max-w-[280px] truncate text-slate-300" title={ev.raw_input}>
                          {ev.raw_input || "—"}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={
                              ev.status === "error"
                                ? "text-red-400"
                                : "text-emerald-400"
                            }
                          >
                            {ev.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-400 tabular-nums">
                          {ev.latency_ms != null ? `${(ev.latency_ms / 1000).toFixed(2)}s` : "—"}
                        </td>
                        <td className="py-3 px-4">
                          <button
                            type="button"
                            onClick={() => setSelectedEvent(ev)}
                            className="text-emerald-400 hover:text-emerald-300 text-sm font-medium"
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {events.length === 0 && !eventsLoading && (
                <div className="p-12 text-center text-slate-500">
                  No events match filters.
                </div>
              )}
            </div>
          </section>
        </div>
      </main>

      {/* Event detail modal */}
      {selectedEvent && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
          onClick={() => setSelectedEvent(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-semibold text-white">Event detail</h3>
                <button
                  type="button"
                  onClick={() => copyToClipboard(JSON.stringify(selectedEvent, null, 2), "all")}
                  className="px-3 py-1 rounded-lg text-xs font-medium bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/30 transition-colors"
                >
                  {copyStatus["all"] ? "Copied!" : "Copy All (JSON)"}
                </button>
              </div>
              <button
                type="button"
                onClick={() => setSelectedEvent(null)}
                className="p-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              >
                ×
              </button>
            </div>
            <div className="p-6 overflow-auto space-y-4 text-sm">
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Time</p>
                <p className="text-slate-200">{selectedEvent.created_at ? new Date(selectedEvent.created_at).toLocaleString() : "—"}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">IP & location</p>
                <p className="text-slate-200">{selectedEvent.client_ip || "—"} — {[selectedEvent.city, selectedEvent.region, selectedEvent.country].filter(Boolean).join(", ") || "—"}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">User-Agent</p>
                <p className="text-slate-400 break-all text-xs">{selectedEvent.user_agent || "—"}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Input (raw)</p>
                <pre className="whitespace-pre-wrap break-words rounded-lg bg-slate-800 p-3 max-h-32 overflow-auto text-slate-300 text-xs">
                  {selectedEvent.raw_input || "—"}
                </pre>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Output (structured)</p>
                {(() => {
                  const outputData = selectedEvent.output_json as any;
                  const items: GroceryItemType[] = Array.isArray(outputData) ? outputData : (outputData?.items || []);
                  
                  if (items.length > 0) {
                    return (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden max-h-96 overflow-y-auto">
                        {items.map((item, i) => (
                          <GroceryItem
                            key={item.id || String(i)}
                            item={{ ...item, id: item.id || String(i), checked: false }}
                            onToggle={() => {}}
                            onSelect={() => {}}
                          />
                        ))}
                      </div>
                    );
                  }
                  
                  return (
                    <pre className="whitespace-pre-wrap break-words rounded-lg bg-slate-800 p-3 max-h-64 overflow-auto text-slate-300 text-xs">
                      {JSON.stringify(selectedEvent.output_json, null, 2)}
                    </pre>
                  );
                })()}
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Status & latency</p>
                <p className="text-slate-200">{selectedEvent.status} — {selectedEvent.latency_ms != null ? `${(selectedEvent.latency_ms / 1000).toFixed(2)}s` : "—"}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
