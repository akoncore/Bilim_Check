import {useRef, useState} from "react";
import {api, formatDate, navigate} from "./api";
import {Form, Hero, Message, Metrics} from "./shared";

export function Login() {
  async function register(values) {
    await api("/login/", {name: values.get("name"), grade: Number(values.get("grade"))});
    navigate("/home/");
  }
  return <div className="split">
    <Hero label="Математика диагностикасы" title="Математикадан деңгейіңді анықта">
      Өз сыныбыңа дейінгі есептерді шығарып, қай тақырыпты қайталау керегін біл.
    </Hero>
    <Form action={register} label="Жалғастыру">
      <h2>Тестке тіркелу</h2>
      <label>Аты-жөнің<input name="name" required maxLength={120} autoComplete="name" placeholder="Аты-жөніңді жаз"/></label>
      <label>Сыныбың<select name="grade" required defaultValue=""><option value="">Сыныпты таңда</option>
        {Array.from({length: 11}, (_, i) => <option key={i} value={i + 1}>{i + 1}-сынып</option>)}
      </select></label>
    </Form>
  </div>;
}

export function Home({data}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function start(band) {
    setBusy(true);
    setError("");
    try {
      const attempt = await api("/test/", {band});
      navigate(`/test/?id=${attempt.id}`);
    } catch (failure) {
      setError(failure.message);
      setBusy(false);
    }
  }
  const firstName = data.student.name.split(/\s+/)[0];
  return <div className="stack">
    <Hero label="Математика диагностикасы" title={`Сәлем, ${firstName}!`}>
      {data.student.grade}-сынып · Өзіңе қолжетімді бөлімді таңда.
    </Hero>
    <div className="row"><h2>Сынып бөлімдері</h2>
      {data.last && <a href={`/test/result/?id=${data.last}`}>Соңғы нәтиже</a>}</div>
    <div className="grid">{data.bands.map((band) => {
      const blocked = data.active && data.active.band !== band.id;
      const available = band.allowed && !blocked;
      const label = available ? (data.active ? "Тестті жалғастыру" : "Тестті бастау") : "Жабық";
      const range = band.min === data.student.grade ? band.min : `${band.min}–${data.student.grade}`;
      const description = !band.allowed ? "Сенің сыныбыңа қолжетімсіз"
        : blocked ? "Алдымен басталған тестті аяқта" : `${range}-сынып тақырыптары`;
      return <article key={band.id} className={`card band ${available ? "available" : ""}`}>
        <strong>{band.id.replace("-", "–")}</strong><h3>Сыныптар</h3><p className="muted">{description}</p>
        <button disabled={!available || busy} onClick={() => start(band.id)}>{label}</button>
      </article>;
    })}</div><Message value={error}/>
  </div>;
}

export function Quiz({data}) {
  const [items, setItems] = useState(data.questions);
  const [index, setIndex] = useState(() => {
    const first = data.questions.findIndex((item) => item.selected === null);
    return first < 0 ? data.questions.length - 1 : first;
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const heading = useRef(null);
  const item = items[index];
  const answered = items.filter((q) => q.selected !== null).length;
  const last = index === items.length - 1;

  async function perform(action) {
    setBusy(true);
    setError("");
    try { await action(); } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  function go(target) {
    setError("");
    setIndex(target);
    heading.current?.focus();
  }
  function answer(selected) {
    return perform(async () => {
      await api(`/test/${data.id}/answer/`, {question_id: item.id, selected});
      setItems((current) => current.map((question) => question.id === item.id ? {...question, selected} : question));
    });
  }
  async function next() {
    if (!last) return go(index + 1);
    const pending = items.findIndex((question) => question.selected === null);
    if (pending >= 0) return go(pending);
    await perform(async () => {
      await api(`/test/${data.id}/finish/`, {});
      navigate(`/test/result/?id=${data.id}`);
    });
  }
  return <section className="narrow stack">
    <div className="row"><a href="/home/">Бөлімдерге қайту</a><span className="pill">{answered} / {items.length} жауап сақталды</span></div>
    <progress value={answered} max={items.length} aria-label="Тест барысы"/>
    <div className="card stack">
      <div className="row"><span className="pill">{item.grade}-сынып · {item.topic}</span><small>{index + 1} / {items.length} есеп</small></div>
      <h1 className="question" tabIndex={-1} ref={heading}>{item.prompt}</h1>
      <div className="stack" role="group" aria-label="Жауап нұсқалары">
        {item.options.map((option, selected) => <button key={selected} className="option" disabled={busy}
          aria-pressed={item.selected === selected} onClick={() => answer(selected)}>
          <span className="letter">{String.fromCharCode(65 + selected)}</span>{option}
        </button>)}
      </div>
      <div className="row"><button className="secondary" disabled={busy || index === 0} onClick={() => go(index - 1)}>Алдыңғы есеп</button>
        <button disabled={busy || item.selected === null} onClick={next}>{last ? "Тестті аяқтау" : "Келесі есеп"}</button></div>
      <Message value={error}/>
    </div>
  </section>;
}

export function Result({data}) {
  return <div className="stack">
    <Hero label="Тест аяқталды" title="Сенің нәтижең">{formatDate(data.finished_at)}</Hero>
    <Metrics data={data}/><div><a className="button" href="/home/">Бөлімдерге қайту</a></div>
  </div>;
}
