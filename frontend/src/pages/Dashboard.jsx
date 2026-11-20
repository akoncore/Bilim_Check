import {QuestionBank} from "../components/QuestionBank";
import {ResultDetail, ResultsList} from "../components/TeacherResults";
import {useResource} from "../hooks/useResource";
import {TeacherLayout} from "../layouts/TeacherLayout";

export function Dashboard({params}) {
  const view = params.get("view") || "results";
  const id = params.get("id");
  const filters = new URLSearchParams();
  for (const key of ["page", "page_size", "q", "grade", "status"]) {
    if (params.get(key)) filters.set(key, params.get(key));
  }
  const endpoints = {students: "students", student: `student/${id}/result`, detail: `results/${id}`};
  const resource = useResource(view === "bank" ? null : `/admin/${endpoints[view] || "results"}/?${filters}`);

  let content = <p role="status">Жүктелуде…</p>;
  if (view === "bank") content = <QuestionBank/>;
  else if (resource?.error) content = <p role="alert" className="error">{resource.error}</p>;
  else if (resource?.data) content = view === "detail" ? <ResultDetail data={resource.data}/>
    : <ResultsList data={resource.data} view={view} id={id} filters={filters}/>;
  return <TeacherLayout view={view}>{content}</TeacherLayout>;
}
