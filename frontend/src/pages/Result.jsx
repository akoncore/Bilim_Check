import {formatDate} from "../api";
import {Hero, Metrics} from "../components/ui";

export function Result({data}) {
  return <div className="stack">
    <Hero label="Тест аяқталды" title="Сенің нәтижең">{formatDate(data.finished_at)}</Hero>
    <Metrics data={data}/><div><a className="button" href="/home/">Бөлімдерге қайту</a></div>
  </div>;
}
