/** Simple state management for the widget using Preact signals pattern. */

import type { ChatMessage, WidgetConfig } from "./types";

export interface WidgetState {
  isOpen: boolean;
  messages: ChatMessage[];
  isStreaming: boolean;
  sessionId: string | null;
  config: WidgetConfig | null;
  leadCaptured: boolean;
  error: string | null;
}

type Listener = () => void;

let state: WidgetState = {
  isOpen: false,
  messages: [],
  isStreaming: false,
  sessionId: null,
  config: null,
  leadCaptured: false,
  error: null,
};

const listeners = new Set<Listener>();

export function getState(): WidgetState {
  return state;
}

export function setState(partial: Partial<WidgetState>) {
  state = { ...state, ...partial };
  listeners.forEach((fn) => fn());
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
