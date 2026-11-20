import {useEffect} from "react";
import {useResource} from "./hooks/useResource";
import {SiteLayout} from "./layouts/SiteLayout";
import {Dashboard} from "./pages/Dashboard";
import {TeacherLogin} from "./pages/TeacherLogin";
import {Home} from "./pages/Home";
import {Login} from "./pages/Login";
import {Quiz} from "./pages/Quiz";
import {Result} from "./pages/Result";

const path = location.pathname.replace(/\/$/, "");
const params = new URLSearchParams(location.search);
const id = params.get("id") || "";
const teacher = path === "/admin";
const test = path === "/test" || path === "/test/result";
const validId = /^[0-9]{1,18}$/.test(id);
const query = teacher ? "/admin/session/"
  : test ? (validId ? `/test/${id}/${path === "/test/result" ? "result/" : ""}` : null)
    : "/home/";

export function App() {
  const state = useResource(query);
  const anonymous = state?.status === 401;
  const data = state?.data;
  let redirect;
  if (test && !validId) redirect = "/home/";
  else if (!teacher && anonymous && path !== "/login") redirect = "/login/";
  else if (data && path === "/login") redirect = "/home/";
  else if (data?.finished_at && path === "/test") redirect = `/test/result/?id=${id}`;
  useEffect(() => {
    if (redirect) location.replace(redirect);
  }, [redirect]);

  let page = <p role="status">Жүктелуде…</p>;
  if (!redirect) {
    if (state?.error && !anonymous) {
      page = <section className="card stack"><h1>Бетті ашу мүмкін болмады</h1>
        <p className="error">{state.error}</p><a href="/home/">Басты бет</a></section>;
    } else if (teacher && state) page = data ? <Dashboard params={params}/> : <TeacherLogin/>;
    else if (path === "/login" && anonymous) page = <Login/>;
    else if (data && path === "/test") page = <Quiz data={data}/>;
    else if (data && path === "/test/result") page = <Result data={data}/>;
    else if (data) page = <Home data={data}/>;
  }
  return <SiteLayout teacherArea={teacher} authenticated={Boolean(data)}>{page}</SiteLayout>;
}
