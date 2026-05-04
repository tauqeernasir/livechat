/** Main chat panel component. */

import { h } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import type { ChatMessage, WidgetConfig } from "../types";
import * as api from "../api";
import { getState, setState, subscribe } from "../state";
import { Message } from "./Message";
import { LeadForm } from "./LeadForm";

interface Props {
    config: WidgetConfig;
    onClose: () => void;
}

export function ChatPanel({ config, onClose }: Props) {
    const [messages, setMessages] = useState<ChatMessage[]>(getState().messages);
    const [input, setInput] = useState("");
    const [isStreaming, setIsStreaming] = useState(false);
    const [leadCaptured, setLeadCaptured] = useState(getState().leadCaptured);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        return subscribe(() => {
            const s = getState();
            setMessages([...s.messages]);
            setIsStreaming(s.isStreaming);
            setLeadCaptured(s.leadCaptured);
        });
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const ensureSession = async () => {
        if (!getState().sessionId) {
            const session = await api.createSession();
            api.setSessionToken(session.access_token);
            setState({ sessionId: session.session_id });
        }
    };

    const handleSend = async () => {
        const text = input.trim();
        if (!text || isStreaming) return;

        setInput("");
        await ensureSession();

        const userMsg: ChatMessage = { role: "user", content: text };
        const currentMessages = [...getState().messages, userMsg];
        setState({ messages: currentMessages, isStreaming: true });

        // Add placeholder for assistant response
        const assistantMsg: ChatMessage = { role: "assistant", content: "" };
        setState({ messages: [...currentMessages, assistantMsg] });

        try {
            for await (const chunk of api.streamChat(currentMessages)) {
                if (chunk.done) break;
                assistantMsg.content += chunk.content;
                setState({ messages: [...currentMessages, { ...assistantMsg }] });
            }
        } catch {
            assistantMsg.content = "Sorry, something went wrong. Please try again.";
            setState({ messages: [...currentMessages, { ...assistantMsg }] });
        } finally {
            setState({ isStreaming: false });
        }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleLeadSubmit = async (data: Record<string, string>) => {
        try {
            const { email, name, ...rest } = data;
            const session = await api.submitLead({ email, name, metadata: rest });
            api.setSessionToken(session.access_token);
            setState({ sessionId: session.session_id, leadCaptured: true });
        } catch (err) {
            console.error("[Lagent Widget] Lead submission failed:", err);
        }
    };

    const showLeadForm =
        config.lead_capture_enabled && !leadCaptured && messages.length === 0;

    return (
        <div
            style={{
                position: "fixed",
                bottom: "88px",
                ...(config.position?.includes("left") ? { left: "20px" } : { right: "20px" }),
                width: "380px",
                maxWidth: "calc(100vw - 32px)",
                height: "520px",
                maxHeight: "calc(100vh - 120px)",
                borderRadius: "16px",
                backgroundColor: "#fff",
                boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
                fontFamily:
                    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                zIndex: "2147483646",
            }}
        >
            {/* Header */}
            <div
                style={{
                    padding: "16px",
                    backgroundColor: config.primary_color,
                    color: "#fff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    flexShrink: 0,
                }}
            >
                <span style={{ fontWeight: 600, fontSize: "15px" }}>Chat</span>
                <button
                    onClick={onClose}
                    aria-label="Close chat"
                    style={{
                        background: "none",
                        border: "none",
                        color: "#fff",
                        cursor: "pointer",
                        padding: "4px",
                        fontSize: "18px",
                        lineHeight: 1,
                    }}
                >
                    ✕
                </button>
            </div>

            {/* Body */}
            {showLeadForm ? (
                <LeadForm
                    fields={config.lead_capture_fields}
                    primaryColor={config.primary_color}
                    onSubmit={handleLeadSubmit}
                />
            ) : (
                <>
                    {/* Messages */}
                    <div
                        style={{
                            flex: 1,
                            overflowY: "auto",
                            padding: "12px 0",
                        }}
                    >
                        {messages.length === 0 && (
                            <div
                                style={{
                                    padding: "20px 16px",
                                    textAlign: "center",
                                    color: "#888",
                                    fontSize: "14px",
                                }}
                            >
                                {config.welcome_message}
                            </div>
                        )}
                        {messages.map((msg, i) => (
                            <Message
                                key={i}
                                message={msg}
                                primaryColor={config.primary_color}
                            />
                        ))}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div
                        style={{
                            padding: "12px 16px",
                            borderTop: "1px solid #eee",
                            display: "flex",
                            gap: "8px",
                            flexShrink: 0,
                        }}
                    >
                        <input
                            value={input}
                            onInput={(e) =>
                                setInput((e.target as HTMLInputElement).value)
                            }
                            onKeyDown={handleKeyDown}
                            placeholder={config.placeholder_text}
                            disabled={isStreaming}
                            style={{
                                flex: 1,
                                padding: "10px 12px",
                                borderRadius: "8px",
                                border: "1px solid #ddd",
                                fontSize: "14px",
                                outline: "none",
                                fontFamily: "inherit",
                            }}
                        />
                        <button
                            onClick={handleSend}
                            disabled={isStreaming || !input.trim()}
                            style={{
                                padding: "10px 16px",
                                borderRadius: "8px",
                                backgroundColor: config.primary_color,
                                color: "#fff",
                                border: "none",
                                cursor: isStreaming || !input.trim() ? "default" : "pointer",
                                opacity: isStreaming || !input.trim() ? 0.5 : 1,
                                fontSize: "14px",
                                fontFamily: "inherit",
                            }}
                        >
                            Send
                        </button>
                    </div>
                </>
            )}

            {/* Footer */}
            <div
                style={{
                    padding: "6px",
                    textAlign: "center",
                    fontSize: "11px",
                    color: "#aaa",
                    borderTop: "1px solid #f5f5f5",
                    flexShrink: 0,
                }}
            >
                Powered by Lagent
            </div>
        </div>
    );
}
