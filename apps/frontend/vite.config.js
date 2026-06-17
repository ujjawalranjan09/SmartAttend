import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";
export default defineConfig({
    plugins: [
        react(),
        tailwindcss(),
        VitePWA({
            registerType: "autoUpdate",
            manifest: false, // we ship /public/manifest.webmanifest
            includeAssets: ["favicon.svg", "icons/icon-192.png", "icons/icon-512.png"],
            workbox: {
                globPatterns: ["**/*.{js,css,html,svg,png,webmanifest}"],
                runtimeCaching: [
                    {
                        urlPattern: /^https:\/\/api\..*/i,
                        handler: "NetworkFirst",
                        options: {
                            cacheName: "api-cache",
                            networkTimeoutSeconds: 5,
                            expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 },
                        },
                    },
                ],
            },
        }),
    ],
    resolve: {
        alias: { "@": path.resolve(__dirname, "./src") },
    },
    server: {
        port: 5173,
        host: true,
        proxy: {
            "/api": { target: "http://localhost:8000", changeOrigin: true },
        },
    },
    build: {
        rollupOptions: {
            input: {
                main: path.resolve(__dirname, "index.html"),
                "classroom-display": path.resolve(__dirname, "classroom-display.html"),
            },
        },
    },
});
