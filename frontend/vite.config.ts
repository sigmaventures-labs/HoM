import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig(async () => {
  const tailwindcss = (await import("@tailwindcss/vite")).default;

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      // Prefer TS/TSX files over JS when the same basename exists
      extensions: [".tsx", ".ts", ".jsx", ".js", ".json"],
    },
    server: {
      port: 5173,
      strictPort: false,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});


