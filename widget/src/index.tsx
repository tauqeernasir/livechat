/** Main widget entry point — mounts into Shadow DOM. */

import { h, render } from "preact";
import { useEffect, useState } from "preact/hooks";
import * as api from "./api";
import { getState, setState, subscribe } from "./state";
import type { WidgetConfig } from "./types";
import { Bubble } from "./components/Bubble";
import { ChatPanel } from "./components/ChatPanel";

function Widget({ config }: { config: WidgetConfig }) {
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        return subscribe(() => {
            // re-render on state changes if needed
        });
    }, []);

    const toggle = () => setIsOpen((o) => !o);

    return (
        <>
            {isOpen && <ChatPanel config={config} onClose={toggle} />}
            <Bubble
                onClick={toggle}
                primaryColor={config.primary_color}
                iconUrl={config.icon_url}
                isOpen={isOpen}
                position={config.position}
            />
        </>
    );
}

/** Initialize and mount the widget. Called by the loader script. */
export async function init(baseUrl: string, widgetKey: string) {
    api.configure(baseUrl, widgetKey);

    try {
        const config = await api.fetchConfig();
        setState({ config });

        // Create Shadow DOM host
        const host = document.createElement("div");
        host.id = "lagent-widget-host";
        document.body.appendChild(host);

        const shadow = host.attachShadow({ mode: "closed" });

        // Mount Preact into shadow root
        const container = document.createElement("div");
        shadow.appendChild(container);

        render(<Widget config={config} />, container);
    } catch (err) {
        console.error("[Lagent Widget] Failed to initialize:", err);
    }
}

// Auto-init if loaded via script tag with data attributes
if (typeof document !== "undefined") {
    const currentScript = document.currentScript as HTMLScriptElement | null;
    if (currentScript) {
        const key =
            currentScript.getAttribute("data-key") ||
            new URL(currentScript.src).searchParams.get("key");
        if (key) {
            const baseUrl =
                currentScript.getAttribute("data-base-url") ||
                new URL(currentScript.src).origin;
            // Defer initialization to after DOM is ready
            if (document.readyState === "loading") {
                document.addEventListener("DOMContentLoaded", () => init(baseUrl, key));
            } else {
                init(baseUrl, key);
            }
        }
    }
}
