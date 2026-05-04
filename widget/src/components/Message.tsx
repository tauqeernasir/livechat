/** Single chat message bubble. */

import { h } from "preact";
import type { ChatMessage } from "../types";

interface Props {
    message: ChatMessage;
    primaryColor: string;
}

export function Message({ message, primaryColor }: Props) {
    const isUser = message.role === "user";

    return (
        <div
            style={{
                display: "flex",
                justifyContent: isUser ? "flex-end" : "flex-start",
                marginBottom: "8px",
                padding: "0 12px",
            }}
        >
            <div
                style={{
                    maxWidth: "80%",
                    padding: "10px 14px",
                    borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                    backgroundColor: isUser ? primaryColor : "#f0f0f0",
                    color: isUser ? "#fff" : "#1a1a1a",
                    fontSize: "14px",
                    lineHeight: "1.45",
                    wordBreak: "break-word",
                }}
            >
                {message.content}
            </div>
        </div>
    );
}
