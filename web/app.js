const main = document.querySelector("#main");
const nav = document.querySelector("#nav");
const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[char]);
const flash = '<p class="flash" id="flash" role="status" aria-live="polite"></p>';
const date = (value) => value ? new Intl.DateTimeFormat("kk-KZ", {
  dateStyle: "short", timeStyle: "short",
}).format(new Date(value)) : "—";
const open = (path) => { location.href = path; };
const bind = (selector, event, callback) => document.querySelector(selector)?.addEventListener(event, callback);
const post = (path, body = {}) => api(path, body);

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
  };
  const response = await fetch("/api" + path, options);
  const data = await response.json();
  if (!response.ok) throw Object.assign(new Error(data.error), {status: response.status});
  return data;
}

function message(value, error = true) {
  const target = document.querySelector("#flash");
  if (target) {
    target.className = error ? "flash error" : "flash success";
    target.textContent = value;
  }
}

function submit(selector, action) {
  bind(selector, "submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    message("");
    try { await action(values); } catch (error) { message(error.message); }
    finally { button.disabled = false; }
  });
}

function studentNav() {
  nav.innerHTML = '<a href="/admin/">Мұғалімге</a><button type="button" class="secondary" id="exit">Шығу</button>';
  bind("#exit", "click", async () => {
    try { await post("/logout"); open("/login/"); } catch (error) { message(error.message); }
  });
}

function login() {
  main.innerHTML = `<div class="split"><section class="hero"><span class="eyebrow">Математика диагностикасы</span>
    <h1>Математикадан деңгейіңді анықта</h1><p>Өз сыныбыңа дейінгі есептерді шығарып, қай тақырыпты қайталау керегін біл.</p></section>
    <form class="card stack" id="login"><h2>Тестке тіркелу</h2>
    <label>Аты-жөнің<input name="name" required maxlength="120" autocomplete="name" placeholder="Аты-жөніңді жаз"></label>
    <label>Сыныбың<select name="grade" required><option value="">Сыныпты таңда</option>
    ${Array.from({length: 11}, (_, i) => `<option value="${i + 1}">${i + 1}-сынып</option>`).join("")}</select></label>
    <button type="submit">Жалғастыру</button>${flash}</form></div>`;
  submit("#login", async (values) => {
    await post("/login", {name: values.get("name"), grade: Number(values.get("grade"))});
    open("/home/");
  });
}

function home(data) {
  studentNav();
  const firstName = escape(data.student.name.split(/\s+/)[0]);
  main.innerHTML = `<div class="stack"><section class="hero"><span class="eyebrow">Математика диагностикасы</span>
    <h1>Сәлем, ${firstName}!</h1><p>${data.student.grade}-сынып · Өзіңе қолжетімді бөлімді таңда.</p></section>
    <div class="row"><h2>Сынып бөлімдері</h2>${data.last ? `<a href="/test/result/?id=${data.last}">Соңғы нәтиже</a>` : ""}</div>
    <div class="grid">${data.bands.map((band) => {
      const blockedByActive = data.active && data.active.band !== band.id;
      const available = band.allowed && !blockedByActive;
      const span = band.id.replace("-", "–");
      const description = !band.allowed ? "Сенің сыныбыңа қолжетімсіз" : blockedByActive ? "Алдымен басталған тестті аяқта" : `${band.min}–${data.student.grade}-сынып тақырыптары`.replace(/^(\d+)–\1-/, "$1-");
      return `<article class="card band ${available ? "available" : ""}"><strong>${span}</strong><h3>Сыныптар</h3>
      <p class="muted">${description}</p><button type="button" data-band="${band.id}" ${available ? "" : "disabled"}>
      ${available ? (data.active ? "Тестті жалғастыру" : "Тестті бастау") : "Жабық"}</button></article>`;
    }).join("")}</div>${flash}</div>`;
  let starting = false;
  document.querySelectorAll("[data-band]").forEach((button) => button.addEventListener("click", async () => {
    if (starting) return;
    starting = true;
    button.disabled = true;
    try {
      const test = await post("/test", {band: button.dataset.band});
      open("/test/?id=" + test.id);
    } catch (error) {
      message(error.message);
      starting = false;
      button.disabled = false;
    }
  }));
}

function test(data) {
  studentNav();
  const items = data.questions;
  let index = items.findIndex((item) => item.selected === null);
  if (index === -1) index = items.length - 1;
  if (data.finished_at) return open("/test/result/?id=" + data.id);

  function render(focus = false) {
    const item = items[index];
    const answered = items.filter((q) => q.selected !== null).length;
    const last = index === items.length - 1;
    main.innerHTML = `<section class="narrow stack">
      <div class="row"><a href="/home/">Бөлімдерге қайту</a><span class="pill">${answered} / ${items.length} жауап сақталды</span></div>
      <progress value="${answered}" max="${items.length}" aria-label="Тест барысы"></progress>
      <div class="card stack"><div class="row"><span class="pill">${item.grade}-сынып · ${escape(item.topic)}</span>
      <small>${index + 1} / ${items.length} есеп</small></div>
      <h1 class="question" id="question" tabindex="-1">${escape(item.prompt)}</h1>
      <div class="stack" role="group" aria-label="Жауап нұсқалары">${item.options.map((option, i) =>
        `<button type="button" class="option" data-option="${i}" aria-pressed="${item.selected === i}"><span class="letter">${String.fromCharCode(65+i)}</span>${escape(option)}</button>`).join("")}</div>
      <div class="row"><button type="button" class="secondary" id="prev" ${index ? "" : "disabled"}>Алдыңғы есеп</button>
      <button type="button" id="next" ${item.selected === null ? "disabled" : ""}>${last ? "Тестті аяқтау" : "Келесі есеп"}</button></div>
      ${flash}</div></section>`;
    if (focus) document.querySelector("#question").focus();
    const actionButtons = [...main.querySelectorAll("button")];
    function busy(value) {
      actionButtons.forEach((button) => {
        button.disabled = value || (button.id === "prev" && index === 0) || (button.id === "next" && item.selected === null);
      });
    }
    main.querySelectorAll("[data-option]").forEach((button) => button.addEventListener("click", async () => {
      const selected = Number(button.dataset.option);
      busy(true);
      try {
        await post(`/test/${data.id}/answer`, {question_id: item.id, selected});
        item.selected = selected;
        render();
        main.querySelector(`[data-option="${selected}"]`).focus();
      } catch (error) { busy(false); message(error.message); }
    }));
    bind("#prev", "click", () => { index--; render(true); });
    bind("#next", "click", async () => {
      if (!last) { index++; render(true); return; }
      const pending = items.findIndex((q) => q.selected === null);
      if (pending >= 0) { index = pending; render(true); return; }
      busy(true);
      try { await post(`/test/${data.id}/finish`); open("/test/result/?id=" + data.id); }
      catch (error) { busy(false); message(error.message); }
    });
  }
  render();
}

function metrics(data) {
  const total = data.grades.reduce((sum, item) => sum + item.total, 0);
  const correct = data.grades.reduce((sum, item) => sum + item.correct, 0);
  const answered = data.grades.reduce((sum, item) => sum + item.answered, 0);
  const recommendation = data.recommended_grade
    ? `${data.recommended_grade}-сынып тақырыптарын қайталау`
    : answered < total ? "Нәтиже жиналуда" : "Барлық тексерілген сынып бойынша 70% межесіне жетті";
  const table = (rows, withTopic) => `<div class="scroll"><table><thead><tr><th>Сынып</th>
    ${withTopic ? "<th>Тақырып</th>" : ""}<th>Дұрыс</th><th>Қате</th><th>Жауапсыз</th></tr></thead>
    <tbody>${rows.map((row) => `<tr><td>${row.grade}-сынып</td>${withTopic ? `<td>${escape(row.topic)}</td>` : ""}
    <td>${row.correct} / ${row.total}</td><td>${row.answered - row.correct}</td><td>${row.total - row.answered}</td></tr>`).join("")}</tbody></table></div>`;
  return `<section class="card stack"><div class="row"><div><small>Дұрыс жауап</small><p class="metric">${correct} / ${total}</p></div>
    <div><small>Ұсыныс</small><h3>${recommendation}</h3></div></div></section>
    <section class="card stack"><h2>Сыныптар бойынша</h2>${table(data.grades, false)}
    <h2>Тақырыптар бойынша</h2>${table(data.topics, true)}</section>`;
}

function result(data) {
  studentNav();
  main.innerHTML = `<div class="stack"><section class="hero"><span class="eyebrow">Тест аяқталды</span><h1>Сенің нәтижең</h1>
    <p>${date(data.finished_at)}</p></section>${metrics(data)}<div><a class="button" href="/home/">Бөлімдерге қайту</a></div>${flash}</div>`;
}

function adminLogin() {
  main.innerHTML = `<form class="narrow card stack" id="admin-login"><h1>Мұғалімге кіру</h1>
    <label>Құпиясөз<input name="password" type="password" autocomplete="current-password" required></label>
    <div><button type="submit">Кіру</button></div>${flash}</form>`;
  submit("#admin-login", async (values) => {
    await post("/admin/login", {password: values.get("password")});
    open("/admin/");
  });
}

async function admin(params) {
  try { await api("/admin/session"); }
  catch (error) { if (error.status === 401) return adminLogin(); throw error; }
  nav.innerHTML = '<a href="/home/">Оқушы беті</a><button type="button" id="admin-exit" class="secondary">Шығу</button>';
  bind("#admin-exit", "click", async () => {
    try { await post("/admin/logout"); open("/admin/"); } catch (error) { message(error.message); }
  });
  const view = params.get("view") || "results";
  const page = Number(params.get("page")) || 1;
  const id = Number(params.get("id"));
  const q = params.get("q") || "";
  const heading = `<section class="hero"><span class="eyebrow">Мұғалім кабинеті</span><h1>Диагностика панелі</h1></section>
    <nav aria-label="Кабинет бөлімдері"><a class="button ${view === "results" ? "" : "secondary"}" href="/admin/">Тест нәтижелері</a>
    <a class="button ${view === "students" ? "" : "secondary"}" href="/admin/?view=students">Оқушылар</a>
    <a class="button ${view === "bank" ? "" : "secondary"}" href="/admin/?view=bank">Есептер банкі</a></nav>`;
  let content;
  if (view === "bank") {
    content = `<form class="card stack" id="import"><h2>Есептерді жүктеу</h2>
      <p class="muted">JSON файлында сынып, тақырып, тапсырма, жауап нұсқалары және дұрыс жауаптың нөлден басталатын индексі көрсетіледі.</p>
      <label>JSON файл<input type="file" name="file" accept=".json,application/json" required></label>
      <div><button type="submit">Импорттау</button></div></form>`;
  } else if (view === "detail") {
    const data = await api("/admin/results/" + id);
    content = `<div class="row"><h2>${escape(data.student.name)} · ${data.student.grade}-сынып</h2><span class="pill">${data.finished_at ? "Аяқталды" : "Орындалуда"}</span></div>
      <p>Басталды: ${date(data.started_at)} · Аяқталды: ${date(data.finished_at)}</p>${metrics(data)}
      <section class="card"><h2>Әр есептің жауабы</h2>${data.questions.map((item, i) => {
        const state = item.selected === null ? "Жауапсыз" : item.selected === item.correct ? "Дұрыс" : "Қате";
        return `<details ${state === "Қате" ? "open" : ""}><summary>${i + 1}. ${escape(item.prompt)} · ${state}</summary>
          <p>${item.grade}-сынып · ${escape(item.topic)}</p><p>Оқушы жауабы: ${escape(item.options[item.selected] ?? "—")}</p>
          <p>Дұрыс жауап: ${escape(item.options[item.correct])}</p><p>Жауап уақыты: ${date(item.answered_at)}</p></details>`;
      }).join("")}</section>`;
  } else {
    const students = view === "students";
    const endpoint = students ? "/admin/students" : view === "student" ? `/admin/student/${id}/result` : "/admin/results";
    const data = await api(endpoint + "?" + new URLSearchParams({page, q}));
    const tableHeader = students ? "<th>Тіркелді</th><th>Тест саны</th>" : "<th>Басталды</th><th>Күйі</th><th>Дұрыс</th>";
    const rows = data.items.map((item) => `<tr><td><a href="/admin/?view=${students ? "student" : "detail"}&amp;id=${item.id}">${escape(item.name)}</a></td><td>${item.grade}</td>${
      students ? `<td>${date(item.created_at)}</td><td>${item.attempts}</td>` :
      `<td>${date(item.started_at)}</td><td>${item.finished_at ? "Аяқталды" : `Орындалуда · ${item.answered}/${item.total}`}</td><td>${item.correct}/${item.total}</td>`
    }</tr>`).join("");
    const pages = Math.max(1, Math.ceil(data.total / data.page_size));
    const pageLink = (target, label) => `<a class="button secondary" href="/admin/?${escape(new URLSearchParams({view, id: id || "", q, page: target}))}">${label}</a>`;
    content = `<section class="card stack"><div class="row"><h2>${data.student ? escape(data.student.name) : students ? "Оқушылар" : "Тест нәтижелері"}</h2>
      ${students ? `<form class="actions" method="get"><input type="hidden" name="view" value="students"><label>Аты-жөні бойынша іздеу<input name="q" value="${escape(q)}" maxlength="120"></label><button type="submit">Іздеу</button></form>` : ""}</div>
      ${data.student ? `<p>${data.student.grade}-сынып · Тіркелді: ${date(data.student.created_at)}</p>` : ""}
      ${rows ? `<div class="scroll"><table><thead><tr><th>Аты-жөні</th><th>Сынып</th>${tableHeader}</tr></thead><tbody>${rows}</tbody></table></div>` : "<p>Дерек табылмады.</p>"}
      <div class="row"><span>${data.page} / ${pages} бет · ${data.total} жазба</span><div class="actions">
      ${data.page > 1 ? pageLink(data.page - 1, "Алдыңғы бет") : ""}${data.page < pages ? pageLink(data.page + 1, "Келесі бет") : ""}</div></div></section>`;
  }
  main.innerHTML = `<div class="stack">${heading}${content}${flash}</div>`;
  submit("#import", async (values) => {
    const file = values.get("file");
    if (file.size > 2_000_000) throw new Error("Файл 2 МБ-тан аспауы керек.");
    let bank;
    try { bank = JSON.parse((await file.text()).replace(/^\uFEFF/, "")); }
    catch { throw new Error("JSON файл форматы қате."); }
    const data = await post("/admin/questions/import", bank);
    document.querySelector("#import").reset();
    message(`${data.imported} есеп сақталды.`, false);
  });
}

async function boot() {
  const path = location.pathname.replace(/\/$/, "");
  const params = new URLSearchParams(location.search);
  const id = Number(params.get("id"));
  try {
    if (path === "/admin") return await admin(params);
    if (path === "/login") {
      try { await api("/home"); return open("/home/"); }
      catch (error) { if (error.status === 401) return login(); throw error; }
    }
    if ((path === "/test" || path === "/test/result") && !id) return open("/home/");
    if (path === "/test") return test(await api("/test/" + id));
    if (path === "/test/result") return result(await api(`/test/${id}/result`));
    return home(await api("/home"));
  } catch (error) {
    if (error.status === 401 && path !== "/admin") return open("/login/");
    main.innerHTML = `<section class="card stack"><h1>Бетті ашу мүмкін болмады</h1><p class="error">${escape(error.message)}</p><a href="/home/">Басты бет</a></section>`;
  }
}

boot();
