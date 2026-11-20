import {useState} from "react";

export function Hero({label, title, children}) {
  return <section className="hero">
    <span className="eyebrow">{label}</span><h1>{title}</h1>
    {children && <p>{children}</p>}
  </section>;
}

export function Message({value, success = false}) {
  return <p className={success ? "flash success" : "flash error"} role="status">{value}</p>;
}

export function Form({className = "card stack", action, children, label, ...props}) {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    setBusy(true);
    setNotice(null);
    try {
      const value = await action(new FormData(form), form);
      if (value) setNotice({value, success: true});
    } catch (error) {
      setNotice({value: error.message});
    } finally {
      setBusy(false);
    }
  }
  return <form {...props} className={className} onSubmit={submit}>
    {children}
    <div><button type="submit" disabled={busy}>{label}</button></div>
    <Message {...notice}/>
  </form>;
}

function Scores({rows, withTopic = false}) {
  return <div className="scroll"><table>
    <thead><tr><th>Сынып</th>{withTopic && <th>Тақырып</th>}<th>Дұрыс</th><th>Қате</th><th>Жауапсыз</th></tr></thead>
    <tbody>{rows.map((row) => <tr key={JSON.stringify([row.grade, row.topic])}>
      <td>{row.grade}-сынып</td>{withTopic && <td>{row.topic}</td>}
      <td>{row.correct} / {row.total}</td><td>{row.answered - row.correct}</td><td>{row.total - row.answered}</td>
    </tr>)}</tbody>
  </table></div>;
}

export function Metrics({data}) {
  const total = data.grades.reduce((sum, row) => sum + row.total, 0);
  const correct = data.grades.reduce((sum, row) => sum + row.correct, 0);
  const recommendation = data.recommended_grade ? `${data.recommended_grade}-сынып тақырыптарын қайталау`
    : data.finished_at ? "Барлық тексерілген сынып бойынша 70% межесіне жетті" : "Нәтиже жиналуда";
  return <>
    <section className="card row"><div><small>Дұрыс жауап</small><p className="metric">{correct} / {total}</p></div>
      <div><small>Ұсыныс</small><h3>{recommendation}</h3></div></section>
    <section className="card stack"><h2>Сыныптар бойынша</h2><Scores rows={data.grades}/>
      <h2>Тақырыптар бойынша</h2><Scores rows={data.topics} withTopic/></section>
  </>;
}
