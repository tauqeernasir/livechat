/** Floating bubble launcher button. */

import { h } from "preact";

interface Props {
    onClick: () => void;
    primaryColor: string;
    iconUrl: string | null;
    isOpen: boolean;
}

export function Bubble({ onClick, primaryColor, iconUrl, isOpen }: Props) {
    return (
        <button
            onClick={onClick}
            aria-label={isOpen ? "Close chat" : "Open chat"}
            style={{
                position: "fixed",
                bottom: "20px",
                right: "20px",
                width: "56px",
                height: "56px",
                borderRadius: "50%",
                backgroundColor: primaryColor,
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                transition: "transform 0.2s ease",
                zIndex: "2147483647",
            }}
        >
            {iconUrl ? (
                <img
                    src={iconUrl}
                    alt=""
                    style={{ width: "28px", height: "28px", borderRadius: "50%" }}
                />
            ) : isOpen ? (
                <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="white"
                    stroke-width="2"
                >
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
            ) : (
                <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="white"
                    stroke-width="2"
                >
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
            )}
        </button>
    );
}
