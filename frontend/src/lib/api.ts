import { ParseListRequest, ParseListResponse } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export async function healthCheck(): Promise<{ status: string; version: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}
