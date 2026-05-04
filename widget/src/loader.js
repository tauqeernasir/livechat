/**
 * Lagent Widget Loader (~1KB)
 *
 * Embed via:
 *   <script src="https://your-api.com/widget/embed.js?key=wk_xxx"></script>
 *
 * This tiny script loads the full widget bundle dynamically.
 */
(function () {
    if (typeof window === "undefined") return;
    if (window.__lagentWidgetLoaded) return;
    window.__lagentWidgetLoaded = true;

    var script = document.currentScript;
    if (!script) return;

    var key =
        script.getAttribute("data-key") ||
        new URL(script.src).searchParams.get("key");
    if (!key) {
        console.error("[Lagent Widget] No widget key provided.");
        return;
    }

    var baseUrl =
        script.getAttribute("data-base-url") || new URL(script.src).origin;

    // Load the full widget bundle
    var widgetScript = document.createElement("script");
    widgetScript.src = baseUrl + "/widget/lagent-widget.js";
    widgetScript.setAttribute("data-key", key);
    widgetScript.setAttribute("data-base-url", baseUrl);
    widgetScript.async = true;
    document.head.appendChild(widgetScript);
})();
