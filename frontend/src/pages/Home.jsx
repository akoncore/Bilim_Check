import {api, navigate} from "../api";
import {Hero, Message} from "../components/ui";
import {useMutation} from "../hooks/useMutation";

export function Home({data}) {
  const {run, busy, error} = useMutation();
  function start(band) {
    return run(async () => {
      const attempt = await api("/test/", {band});
      navigate(`/test/?id=${attempt.id}`);
    });
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
