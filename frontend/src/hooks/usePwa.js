import {useEffect, useState, useSyncExternalStore} from "react";

function subscribe(callback) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

export function useOnline() {
  return useSyncExternalStore(subscribe, () => navigator.onLine);
}

let pendingInstall;
const installListeners = new Set();

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  pendingInstall = event;
  for (const update of installListeners) update(event);
});

window.addEventListener("appinstalled", () => {
  pendingInstall = undefined;
  for (const update of installListeners) update(undefined);
});

export function useInstallPrompt() {
  const [prompt, setPrompt] = useState(pendingInstall);
  useEffect(() => {
    installListeners.add(setPrompt);
    setPrompt(pendingInstall);
    return () => { installListeners.delete(setPrompt); };
  }, []);

  async function install() {
    if (!prompt) return;
    pendingInstall = undefined;
    setPrompt(undefined);
    try { await prompt.prompt(); }
    catch (error) { console.warn("App installation could not be started", error); }
  }
  return {available: Boolean(prompt), install};
}
