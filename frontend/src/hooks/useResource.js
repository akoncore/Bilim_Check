import {useEffect, useState} from "react";
import {api} from "../api";

export function useResource(path) {
  const [state, setState] = useState(null);

  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    api(path, undefined, {signal: controller.signal})
      .then((data) => { if (!controller.signal.aborted) setState({path, data}); })
      .catch((failure) => {
        if (!controller.signal.aborted) setState({path, error: failure.message, status: failure.status});
      });
    return () => controller.abort();
  }, [path]);

  return state?.path === path ? state : null;
}
