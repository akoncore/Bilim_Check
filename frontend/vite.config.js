import {createHash} from "node:crypto";
import {readFileSync} from "node:fs";
import {defineConfig} from "vite";

const publicAssets = [
  "/offline.html", "/offline.css", "/manifest.webmanifest",
  "/icons/bilim-192.png", "/icons/bilim-512.png", "/icons/bilim-maskable.png",
];
const apiProxy = {
  "/api": {target: process.env.BACKEND_URL || "http://127.0.0.1:8000", changeOrigin: false},
};
const read = (path) => readFileSync(new URL(path, import.meta.url));

export default defineConfig({
  esbuild: {jsx: "automatic"},
  plugins: [{
    name: "bilim-offline",
    apply: "build",
    generateBundle(_options, bundle) {
      const worker = read("./service-worker.js");
      const hash = createHash("sha256").update(worker);
      for (const asset of publicAssets) hash.update(read("./public" + asset));
      const files = Object.keys(bundle).filter((file) => file.startsWith("assets/")).sort();
      hash.update(JSON.stringify(files));
      const version = hash.digest("hex").slice(0, 16);
      this.emitFile({
        type: "asset",
        fileName: "sw.js",
        source: `const BUILD_VERSION = ${JSON.stringify(version)};\nconst STATIC_FILES = ${JSON.stringify([
          ...publicAssets, ...files.map((file) => "/" + file),
        ])};\n${worker}`,
      });
    },
  }],
  server: {
    proxy: apiProxy,
  },
  preview: {
    proxy: apiProxy,
  },
});
