/** Widget configuration returned from the API. */
export interface WidgetConfig {
  position: string;
  primary_color: string;
  welcome_message: string;
  placeholder_text: string;
  icon_url: string | null;
  lead_capture_enabled: boolean;
  lead_capture_fields: string[];
  allowed_origins: string[];
}

/** A chat message. */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

/** Response from session creation. */
export interface SessionResponse {
  session_id: string;
  access_token: string;
  expires_at: string;
}

/** SSE stream chunk. */
export interface StreamChunk {
  content: string;
  done: boolean;
}
