let csrf;

export async function api(path, body) {
  let options;
  if (body !== undefined) {
    csrf ??= (await api("/csrf/")).csrf;
    options = {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CSRFToken": csrf},
      body: JSON.stringify(body),
    };
  }
  const response = await fetch("/api" + path, options);
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
