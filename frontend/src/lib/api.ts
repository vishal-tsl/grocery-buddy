import { ParseListRequest, ParseListResponse, RecipeRequest, RecipeResponse } from "@/types";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("admin_token");
}

function adminHeaders(): HeadersInit {
  const token = getAdminToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function parseGroceryList(
  text: string
): Promise<ParseListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/parse-list`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text } as ParseListRequest),
  });

  if (!response.ok) {
    throw new Error("Failed to parse grocery list");
  }

  return response.json();
}

export async function recipeToList(
  input: string
): Promise<RecipeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/recipe-to-list`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ input } as RecipeRequest),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to process recipe" }));
    throw new Error(error.detail || "Failed to process recipe");
  }

  return response.json();
}

export async function healthCheck(): Promise<{ status: string; version: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}

// Admin panel (testing)
export async function adminLogin(
  email: string,
  password: string
): Promise<{ token: string; expires_in: number }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(err.detail || "Login failed");
  }
  return response.json();
}

export async function adminEvents(params: {
  date_from?: string;
  date_to?: string;
  country?: string;
  endpoint?: string;
  status?: string;
  q?: string;
  limit?: number;
  offset?: number;
}): Promise<{ data: AdminEvent[]; count: number }> {
  const sp = new URLSearchParams();
  if (params.date_from) sp.set("date_from", params.date_from);
  if (params.date_to) sp.set("date_to", params.date_to);
  if (params.country) sp.set("country", params.country);
  if (params.endpoint) sp.set("endpoint", params.endpoint);
  if (params.status) sp.set("status", params.status);
  if (params.q) sp.set("q", params.q);
  if (params.limit != null) sp.set("limit", String(params.limit));
  if (params.offset != null) sp.set("offset", String(params.offset));
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/events?${sp}`, {
    headers: adminHeaders(),
  });
  if (!response.ok) throw new Error("Failed to fetch events");
  return response.json();
}

export async function adminMetrics(days?: number): Promise<AdminMetrics> {
  const url = days != null ? `${API_BASE_URL}/api/v1/admin/metrics?days=${days}` : `${API_BASE_URL}/api/v1/admin/metrics`;
  const response = await fetch(url, { headers: adminHeaders() });
  if (!response.ok) throw new Error("Failed to fetch metrics");
  return response.json();
}

export async function adminPurge(): Promise<{ deleted: number }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/purge`, {
    method: "POST",
    headers: adminHeaders(),
  });
  if (!response.ok) throw new Error("Failed to purge");
  return response.json();
}

export type AdminEvent = {
  id: number;
  created_at: string;
  request_id: string;
  client_ip: string | null;
  ip_hash: string | null;
  country: string | null;
  region: string | null;
  city: string | null;
  user_agent: string | null;
  endpoint: string;
  raw_input: string;
  output_json: unknown;
  status: string;
  latency_ms: number | null;
};

export type AdminMetrics = {
  days: number;
  total_requests: number;
  unique_ips: number;
  error_count: number;
  error_rate: number;
  avg_latency_ms: number | null;
  by_country: Record<string, number>;
};
