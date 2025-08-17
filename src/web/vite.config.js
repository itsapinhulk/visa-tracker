import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import dsv from '@rollup/plugin-dsv'

export default defineConfig({
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
});
