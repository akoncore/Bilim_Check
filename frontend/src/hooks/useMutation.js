import {useCallback, useRef, useState} from "react";

export function useMutation() {
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = useCallback(async (action) => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      return await action();
    } catch (failure) {
      setError(failure.message);
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }, []);

  return {run, busy, error, clearError: () => setError("")};
}
