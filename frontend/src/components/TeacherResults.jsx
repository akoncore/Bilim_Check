import {formatDate} from "../api";
import {Metrics} from "./ui";

export function ResultDetail({data}) {
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

export function ResultsList({data, view, id, filters}) {
  const students = view === "students";
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  const statuses = [["", "Барлық күй"], ["in_progress", "Орындалуда"], ["completed", "Аяқталды"]];
  function pageLink(url) {
    const query = new URL(url).searchParams;
    query.set("view", view);
    if (id) query.set("id", id);
    return "/admin/?" + query;
  }
  return <section className="card stack">
    <div className="row"><h2>{data.student?.name || (students ? "Оқушылар" : "Тест нәтижелері")}</h2>
    </div>
    {!data.student && <form className="filters" method="get">
      <input type="hidden" name="view" value={view}/>
      <label>Аты-жөні<input name="q" defaultValue={filters.get("q") || ""} maxLength={120}/></label>
      <label>Сынып<select name="grade" defaultValue={filters.get("grade") || ""}>
        <option value="">Барлық сынып</option>
        {Array.from({length:11}, (_, index) => <option key={index} value={index + 1}>{index + 1}-сынып</option>)}
      </select></label>
      {!students && <label>Күйі<select name="status" defaultValue={filters.get("status") || ""}>
        {statuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>}
      <label>Беттегі жазба<select name="page_size" defaultValue={String(data.page_size)}>
        {[...new Set([20, 50, 100, data.page_size])].sort((a, b) => a - b).map((size) =>
          <option key={size} value={size}>{size}</option>)}
      </select></label>
      <button type="submit">Іздеу</button>
    </form>}
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
      {data.previous && <a className="button secondary" href={pageLink(data.previous)}>Алдыңғы бет</a>}
      {data.next && <a className="button secondary" href={pageLink(data.next)}>Келесі бет</a>}
    </div></div>
  </section>;
}
