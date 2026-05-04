/** API client for the widget backend. */

import type { ChatMessage, SessionResponse, StreamChunk, WidgetConfig } from "./types";

let _baseUrl = "";
let _widgetKey = "";
let _sessionToken = "";

export function configure(baseUrl: string, widgetKey: string) {
  _baseUrl = baseUrl.replace(/\/+$/, "");
  _widgetKey = widgetKey;
}

export function setSessionToken(token: string) {
  _sessionToken = token;
}

export function getSessionToken(): string {
  return _sessionToken;
}

export async function fetchConfig(): Promise<WidgetConfig> {
  const res = await fetch(
    `${_baseUrl}/api/v1/widget/config?key=${encodeURIComponent(_widgetKey)}`
  );
  if (!res.ok) throw new Error("Failed to fetch widget config");
  return res.json();
}

export async function createSession(): Promise<SessionResponse> {
  const res = await fetch(`${_baseUrl}/api/v1/widget/session`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Widget-Key": _widgetKey,
    },
  });
  if (!res.ok) throw new Error("Failed to create widget session");
  return res.json();
}

export async function getMessages(): Promise<ChatMessage[]> {
  const res = await fetch(`${_baseUrl}/api/v1/widget/messages`, {
    headers: {
      Authorization: `Bearer ${_sessionToken}`,
    },
  });
  if (!res.ok) return [];
  return res.json();
}

export async function submitLead(data: { email: string; name?: string; metadata?: Record<string, string> }): Promise<SessionResponse> {
  const res = await fetch(`${_baseUrl}/api/v1/widget/lead`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Widget-Key": _widgetKey,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to submit lead");
  return res.json();
}

export async function* streamChat(
  messages: ChatMessage[]
): AsyncGenerator<StreamChunk> {
  const res = await fetch(`${_baseUrl}/api/v1/widget/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${_sessionToken}`,
    },
    body: JSON.stringify({ messages }),
  });

  if (!res.ok || !res.body) {
    throw new Error("Stream request failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) continue;
      try {
        const chunk: StreamChunk = JSON.parse(trimmed.slice(6));
        yield chunk;
      } catch {
        // skip malformed chunks
      }
    }
  }
}
