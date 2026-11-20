import {api, navigate} from "../api";
import {Message} from "../components/ui";
import {useMutation} from "../hooks/useMutation";
import {useInstallPrompt, useOnline} from "../hooks/usePwa";

export function SiteLayout({children, teacherArea, authenticated}) {
  const {available, install} = useInstallPrompt();
  const online = useOnline();
  const {run, busy, error} = useMutation();
  function signOut() {
    return run(async () => {
      await api(teacherArea ? "/admin/logout/" : "/logout/", {});
      navigate(teacherArea ? "/admin/" : "/login/");
    });
  }
  return <>
    <header className="top"><div className="shell bar">
      <a className="brand" href="/home/"><span className="mark" aria-hidden="true">B</span> Bilim Check</a>
      <nav aria-label="Негізгі навигация">
        {teacherArea ? <a href="/home/">Оқушы беті</a> : <a href="/admin/">Мұғалімге</a>}
        {available && <button className="secondary" onClick={install}>Орнату</button>}
        {authenticated && <button className="secondary" disabled={busy} onClick={signOut}>Шығу</button>}
      </nav>
    </div></header>
    <main className="shell stack">
      {!online && <p className="offline-banner" role="status">Интернет байланысы жоқ. Жауаптарды сақтау үшін желіге қосылыңыз.</p>}
      <Message value={error}/>
      {children}
    </main>
    <footer className="shell footer">Bilim Check <span>Математика диагностикасы</span></footer>
  </>;
}
