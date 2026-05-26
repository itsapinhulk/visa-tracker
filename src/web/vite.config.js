import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import dsv from '@rollup/plugin-dsv'

process.env.VITE_HOME_URL ??= 'http://localhost:6001'
process.env.VITE_ANALYTICS_URL ??= 'http://localhost:6001/analytics.js'

export default defineConfig({
    define: {
        __BUILD_TIME__: JSON.stringify(process.env.VITE_BUILD_TIME || String(Date.now())),
    },
    plugins: [
        react(),
        dsv(),
    ],
    server: {
        port: 3000,
    },
    optimizeDeps: {
        force: true,
    },
    base: "./",
});
