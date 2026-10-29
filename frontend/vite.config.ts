import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: proxy REST + WebSocket to the FastAPI server so no CORS/env setup is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "http://localhost:8000", ws: true },
    },
  },
});
