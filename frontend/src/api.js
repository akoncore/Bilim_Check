let csrf;
let csrfRequest;

function getCsrf() {
  if (csrf) return Promise.resolve(csrf);
  csrfRequest ??= api("/csrf/").then((data) => data.csrf).finally(() => { csrfRequest = undefined; });
  return csrfRequest;
}

export async function api(path, body, {signal} = {}) {
  const options = {signal, cache: "no-store", credentials: "same-origin"};
  if (body !== undefined) {
    options.method = "POST";
    options.headers = {"Content-Type": "application/json", "X-CSRFToken": await getCsrf()};
    options.body = JSON.stringify(body);
  }
  let response;
  try { response = await fetch("/api/v1" + path, options); }
  catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Серверге қосылу мүмкін болмады. Байланысты тексеріп, қайта көріңіз.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 403) csrf = undefined;
    throw Object.assign(new Error(data.error || "Сұрауды орындау мүмкін болмады."), {status: response.status});
  }
  if (data.csrf) csrf = data.csrf;
  return data;
}

export const navigate = (url) => location.assign(url);
export const formatDate = (value) => value ? new Intl.DateTimeFormat("kk-KZ", {
  dateStyle: "short", timeStyle: "short",
}).format(new Date(value)) : "—";
