import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Em dev, o Vite roda na 5173 e o Flask na 5000. Isso encaminha
      // chamadas pra /api pro backend, então o frontend pode usar sempre
      // caminho relativo (funciona igual em dev e no build empacotado).
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
});
