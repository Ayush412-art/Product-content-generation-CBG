import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // 127.0.0.1 (not "localhost") so Node doesn't try IPv6 ::1, where Flask isn't listening
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:5000" } },
});
