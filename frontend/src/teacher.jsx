import {useEffect, useState} from "react";
import {api, formatDate, navigate} from "./api";
import {Form, Hero, Metrics} from "./shared";

export function TeacherLogin() {
  async function signIn(values) {
    await api("/admin/login/", {username: values.get("username"), password: values.get("password")});
    navigate("/admin/");
  }
  return <Form className="narrow card stack" action={signIn} label="Кіру">
    <h1>Мұғалімге кіру</h1>
    <label>Пайдаланушы аты<input name="username" autoComplete="username" required maxLength={150}/></label>
    <label>Құпиясөз<input name="password" type="password" autoComplete="current-password" required/></label>
  </Form>;
}

function Bank() {
  async function upload(values, form) {
    const file = values.get("file");
    if (file.size > 2_000_000) throw new Error("Файл 2 МБ-тан аспауы керек.");
    let bank;
    try { bank = JSON.parse((await file.text()).replace(/^\uFEFF/, "")); }
    catch { throw new Error("JSON файл форматы қате."); }
    const data = await api("/admin/questions/import/", bank);
    form.reset();
    return `${data.imported} есеп сақталды.`;
  }
  return <Form action={upload} label="Импорттау">
    <h2>Есептерді жүктеу</h2>
    <p className="muted">JSON файлына сыныпты, тақырыпты, тапсырманы, жауап нұсқаларын және дұрыс жауаптың нөлден басталатын индексін енгізіңіз.</p>
    <label>JSON файл<input type="file" name="file" accept=".json,application/json" required/></label>
  </Form>;
}

function Detail({data}) {
  return <>
    <div className="row"><h2>{data.student.name} · {data.student.grade}-сынып</h2>
      <span className="pill">{data.finished_at ? "Аяқталды" : "Орындалуда"}</span></div>
    <p>Басталды: {formatDate(data.started_at)} · Аяқталды: {formatDate(data.finished_at)}</p>
    <Metrics data={data}/>
    <section className="card"><h2>Әр есептің жауабы</h2>{data.questions.map((item, i) => {
      const state = item.selected === null ? "Жауапсыз" : item.selected === item.correct ? "Дұрыс" : "Қате";
      return <details key={item.id} open={state === "Қате" || undefined}>
        <summary>{i + 1}. {item.prompt} · {state}</summary>
        <p>{item.grade}-сынып · {item.topic}</p><p>Оқушы жауабы: {item.options[item.selected] ?? "—"}</p>
        <p>Дұрыс жауап: {item.options[item.correct]}</p><p>Жауап уақыты: {formatDate(item.answered_at)}</p>
      </details>;
    })}</section>
  </>;
}

function List({data, view, id, q}) {
  const students = view === "students";
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  const pageLink = (page) => "/admin/?" + new URLSearchParams({view, id: id || "", q, page});
  return <section className="card stack">
    <div className="row"><h2>{data.student?.name || (students ? "Оқушылар" : "Тест нәтижелері")}</h2>
      {students && <form className="actions" method="get">
        <input type="hidden" name="view" value="students"/>
        <label>Аты-жөні бойынша іздеу<input name="q" defaultValue={q} maxLength={120}/></label>
        <button type="submit">Іздеу</button>
      </form>}</div>
    {data.student && <p>{data.student.grade}-сынып · Тіркелді: {formatDate(data.student.created_at)}</p>}
    {data.items.length ? <div className="scroll"><table>
      <thead><tr><th>Аты-жөні</th><th>Сынып</th>
        {students ? <><th>Тіркелді</th><th>Тест саны</th></> : <><th>Басталды</th><th>Күйі</th><th>Дұрыс</th></>}
      </tr></thead>
      <tbody>{data.items.map((item) => <tr key={item.id}>
        <td><a href={`/admin/?view=${students ? "student" : "detail"}&id=${item.id}`}>{item.name}</a></td><td>{item.grade}</td>
        {students ? <><td>{formatDate(item.created_at)}</td><td>{item.attempts}</td></> : <>
          <td>{formatDate(item.started_at)}</td><td>{item.finished_at ? "Аяқталды" : `Орындалуда · ${item.answered}/${item.total}`}</td>
          <td>{item.correct}/{item.total}</td></>}
      </tr>)}</tbody>
    </table></div> : <p>Дерек табылмады.</p>}
    <div className="row"><span>{data.page} / {pages} бет · {data.total} жазба</span><div className="actions">
      {data.page > 1 && <a className="button secondary" href={pageLink(data.page - 1)}>Алдыңғы бет</a>}
      {data.page < pages && <a className="button secondary" href={pageLink(data.page + 1)}>Келесі бет</a>}
    </div></div>
  </section>;
}

export function Dashboard({params}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const view = params.get("view") || "results";
  const id = params.get("id");
  const q = params.get("q") || "";
  const page = params.get("page") || "1";
  useEffect(() => {
    if (view === "bank") return;
    const endpoints = {students: "students", student: `student/${id}/result`, detail: `results/${id}`};
    let active = true;
    api(`/admin/${endpoints[view] || "results"}/?${new URLSearchParams({page, q})}`)
      .then((result) => { if (active) setData(result); })
      .catch((failure) => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, [view, id, page, q]);
  return <div className="stack">
    <Hero label="Мұғалім кабинеті" title="Диагностика панелі"/>
    <nav aria-label="Кабинет бөлімдері">{[
      ["results", "Тест нәтижелері", "/admin/"], ["students", "Оқушылар", "/admin/?view=students"],
      ["bank", "Есептер банкі", "/admin/?view=bank"],
    ].map(([key, label, url]) => <a key={key} className={`button ${key === view ? "" : "secondary"}`} href={url}>{label}</a>)}</nav>
    {error ? <p role="alert" className="error">{error}</p> : view === "bank" ? <Bank/> : !data
      ? <p role="status">Жүктелуде…</p> : view === "detail" ? <Detail data={data}/>
        : <List data={data} view={view} id={id} q={q}/>}
  </div>;
}
