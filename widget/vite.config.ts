import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

export default defineConfig({
  plugins: [preact()],
  build: {
    lib: {
      entry: "src/index.tsx",
      name: "LagentWidget",
      formats: ["iife"],
      fileName: () => "lagent-widget.js",
    },
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
    minify: "esbuild",
    outDir: "dist",
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
});
