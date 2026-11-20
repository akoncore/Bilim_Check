import {useRef, useState} from "react";
import {api, navigate} from "../api";
import {Message} from "../components/ui";
import {useMutation} from "../hooks/useMutation";

export function Quiz({data}) {
  const [items, setItems] = useState(data.questions);
  const [index, setIndex] = useState(() => {
    const first = data.questions.findIndex((item) => item.selected === null);
    return first < 0 ? data.questions.length - 1 : first;
  });
  const {run, busy, error, clearError} = useMutation();
  const heading = useRef(null);
  const item = items[index];
  const answered = items.filter((q) => q.selected !== null).length;
  const last = index === items.length - 1;

  function go(target) {
    clearError();
    setIndex(target);
    heading.current?.focus();
  }
  function answer(selected) {
    return run(async () => {
      await api(`/test/${data.id}/answer/`, {question_id: item.id, selected});
      setItems((current) => current.map((question) => question.id === item.id ? {...question, selected} : question));
    });
  }
  async function next() {
    if (!last) return go(index + 1);
    const pending = items.findIndex((question) => question.selected === null);
    if (pending >= 0) return go(pending);
    await run(async () => {
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
