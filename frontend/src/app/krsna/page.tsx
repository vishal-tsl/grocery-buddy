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

  if (loading && !metrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <p className="text-gray-500">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-white">
      <header className="sticky top-0 z-10 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-400">
            ← App
          </Link>
          <h1 className="text-lg font-bold">Admin – Usage (testing)</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handlePurge}
            disabled={purgeLoading}
            className="text-sm px-3 py-1.5 rounded border border-amber-500 text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20"
          >
            {purgeLoading ? "Purging…" : "Purge old"}
          </button>
          <button
            type="button"
            onClick={handleLogout}
            className="text-sm px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            Log out
          </button>
        </div>
      </header>

      <main className="p-4 max-w-6xl mx-auto space-y-6">
        {error && (
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        )}

        {metrics && (
          <section>
            <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">Metrics (last N days)</h2>
            <div className="flex gap-2 mb-2">
              {[7, 14, 30].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDays(d)}
                  className={`px-3 py-1 rounded text-sm ${days === d ? "bg-emerald-600 text-white" : "bg-gray-200 dark:bg-gray-700"}`}
                >
                  {d}d
                </button>
              ))}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-800">
                <p className="text-xs text-gray-500 dark:text-gray-400">Requests</p>
                <p className="text-xl font-bold">{metrics.total_requests}</p>
              </div>
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-800">
                <p className="text-xs text-gray-500 dark:text-gray-400">Unique IPs</p>
                <p className="text-xl font-bold">{metrics.unique_ips}</p>
              </div>
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-800">
                <p className="text-xs text-gray-500 dark:text-gray-400">Errors</p>
                <p className="text-xl font-bold">{metrics.error_count} ({(metrics.error_rate * 100).toFixed(2)}%)</p>
              </div>
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-800">
                <p className="text-xs text-gray-500 dark:text-gray-400">Avg latency</p>
                <p className="text-xl font-bold">{metrics.avg_latency_ms != null ? `${metrics.avg_latency_ms} ms` : "—"}</p>
              </div>
            </div>
            {Object.keys(metrics.by_country).length > 0 && (
              <div className="mt-3 rounded-lg border border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-800">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Top countries</p>
                <p className="text-sm">{Object.entries(metrics.by_country).map(([c, n]) => `${c}: ${n}`).join(", ")}</p>
              </div>
            )}
          </section>
        )}

        <section>
          <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">Events (who, input, output, where)</h2>
          <div className="flex flex-wrap gap-2 mb-3">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
            />
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
            />
            <input
              type="text"
              placeholder="Country"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm w-24"
            />
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
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
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm flex-1 min-w-[120px]"
            />
            <button
              type="button"
              onClick={() => loadEvents()}
              disabled={eventsLoading}
              className="px-3 py-1 rounded bg-emerald-600 text-white text-sm hover:bg-emerald-700 disabled:opacity-50"
            >
              {eventsLoading ? "Loading…" : "Apply"}
            </button>
          </div>
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
            <div className="overflow-x-auto max-h-[60vh]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-100 dark:bg-gray-700">
                  <tr>
                    <th className="text-left p-2">Time</th>
                    <th className="text-left p-2">IP / Location</th>
                    <th className="text-left p-2">Input</th>
                    <th className="text-left p-2">Status</th>
                    <th className="text-left p-2">Latency</th>
                    <th className="text-left p-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev) => (
                    <tr key={ev.id} className="border-t border-gray-200 dark:border-gray-700">
                      <td className="p-2 whitespace-nowrap text-gray-500 dark:text-gray-400">
                        {ev.created_at ? new Date(ev.created_at).toLocaleString() : "—"}
                      </td>
                      <td className="p-2">
                        <span className="font-mono text-xs">{ev.client_ip || "—"}</span>
                        {(ev.country || ev.city) && (
                          <span className="ml-1 text-gray-500">({[ev.city, ev.region, ev.country].filter(Boolean).join(", ")})</span>
                        )}
                      </td>
                      <td className="p-2 max-w-[200px] truncate" title={ev.raw_input}>
                        {ev.raw_input || "—"}
                      </td>
                      <td className="p-2">
                        <span className={ev.status === "error" ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"}>
                          {ev.status}
                        </span>
                      </td>
                      <td className="p-2">{ev.latency_ms != null ? `${ev.latency_ms} ms` : "—"}</td>
                      <td className="p-2">
                        <button
                          type="button"
                          onClick={() => setSelectedEvent(ev)}
                          className="text-emerald-600 dark:text-emerald-400 hover:underline"
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
              <p className="p-4 text-center text-gray-500 dark:text-gray-400">No events match filters.</p>
            )}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Total: {count} events</p>
        </section>
      </main>

      {selectedEvent && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
          onClick={() => setSelectedEvent(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h3 className="font-bold">Event detail</h3>
              <button type="button" onClick={() => setSelectedEvent(null)} className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                ×
              </button>
            </div>
            <div className="p-4 overflow-auto space-y-3 text-sm">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Time</p>
                <p>{selectedEvent.created_at ? new Date(selectedEvent.created_at).toLocaleString() : "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Who (IP, location)</p>
                <p>{selectedEvent.client_ip || "—"} — {[selectedEvent.city, selectedEvent.region, selectedEvent.country].filter(Boolean).join(", ") || "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">User-Agent</p>
                <p className="break-all">{selectedEvent.user_agent || "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Input (raw)</p>
                <pre className="whitespace-pre-wrap break-words rounded bg-gray-100 dark:bg-gray-700 p-2 max-h-32 overflow-auto">
                  {selectedEvent.raw_input || "—"}
                </pre>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Output (structured)</p>
                <pre className="whitespace-pre-wrap break-words rounded bg-gray-100 dark:bg-gray-700 p-2 max-h-64 overflow-auto text-xs">
                  {JSON.stringify(selectedEvent.output_json, null, 2)}
                </pre>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Status / Latency</p>
                <p>{selectedEvent.status} — {selectedEvent.latency_ms != null ? `${selectedEvent.latency_ms} ms` : "—"}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
