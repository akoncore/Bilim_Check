import {useEffect, useState} from "react";
import {createRoot} from "react-dom/client";
import {api, navigate} from "./api";
import {Dashboard, TeacherLogin} from "./teacher";
import {Home, Login, Quiz, Result} from "./student";
import "./style.css";

const path = location.pathname.replace(/\/$/, "");
const params = new URLSearchParams(location.search);
const id = params.get("id");

async function load() {
  if (path === "/admin") {
    try { await api("/admin/session/"); return {teacher: true}; }
    catch (error) { if (error.status === 401) return {}; throw error; }
  }
  try {
    if (path === "/test" || path === "/test/result") {
      if (!/^[0-9]{1,18}$/.test(id || "")) return {redirect: "/home/"};
      const data = await api(`/test/${id}/${path === "/test/result" ? "result/" : ""}`);
      if (path === "/test" && data.finished_at) return {redirect: `/test/result/?id=${id}`};
      return {student: true, data};
    }
    const data = await api("/home/");
    return path === "/login" ? {redirect: "/home/"} : {student: true, data};
  } catch (error) {
    if (error.status !== 401) throw error;
    return path === "/login" ? {} : {redirect: "/login/"};
  }
}

function App() {
  const [state, setState] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    load().then((value) => {
      if (value.redirect) location.replace(value.redirect);
      else setState(value);
    }).catch((failure) => setError(failure.message));
  }, []);

  async function signOut() {
    try {
      await api(state.teacher ? "/admin/logout/" : "/logout/", {});
      navigate(state.teacher ? "/admin/" : "/login/");
    } catch (failure) { setError(failure.message); }
  }
  let page = <p role="status">Жүктелуде…</p>;
  if (error) page = <section className="card stack"><h1>Бетті ашу мүмкін болмады</h1>
    <p className="error">{error}</p><a href="/home/">Басты бет</a></section>;
  else if (state) {
    if (path === "/admin") page = state.teacher ? <Dashboard params={params}/> : <TeacherLogin/>;
    else if (path === "/login") page = <Login/>;
    else if (path === "/test") page = <Quiz data={state.data}/>;
    else if (path === "/test/result") page = <Result data={state.data}/>;
    else page = <Home data={state.data}/>;
  }
  return <>
    <header className="top"><div className="shell bar">
      <a className="brand" href="/home/"><span className="mark" aria-hidden="true">B</span> Bilim Check</a>
      <nav aria-label="Негізгі навигация">
        {path === "/admin" ? <a href="/home/">Оқушы беті</a> : <a href="/admin/">Мұғалімге</a>}
        {(state?.teacher || state?.student) && <button className="secondary" onClick={signOut}>Шығу</button>}
      </nav>
    </div></header>
    <main className="shell">{page}</main>
    <footer className="shell footer">Bilim Check <span>Математика диагностикасы</span></footer>
  </>;
}

createRoot(document.getElementById("root")).render(<App/>);
