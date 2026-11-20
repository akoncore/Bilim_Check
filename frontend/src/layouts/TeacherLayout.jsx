import {Hero} from "../components/ui";

const links = [
  ["results", "Тест нәтижелері", "/admin/"],
  ["students", "Оқушылар", "/admin/?view=students"],
  ["bank", "Есептер банкі", "/admin/?view=bank"],
];

export function TeacherLayout({view, children}) {
  return <div className="stack">
    <Hero label="Мұғалім кабинеті" title="Диагностика панелі"/>
    <nav aria-label="Кабинет бөлімдері">{links.map(([key, label, url]) =>
      <a key={key} className={`button ${key === view ? "" : "secondary"}`} href={url}
        aria-current={key === view ? "page" : undefined}>{label}</a>)}</nav>
    {children}
  </div>;
}
