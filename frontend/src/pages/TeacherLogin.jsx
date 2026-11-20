import {api, navigate} from "../api";
import {Form} from "../components/ui";

export function TeacherLogin() {
  async function signIn(values) {
    await api("/admin/login/", {username: values.get("username"), password: values.get("password")});
    navigate("/admin/");
  }
  return <Form className="narrow card stack" action={signIn} label="Кіру">
    <h1>Мұғалімге кіру</h1>
    <label>Пайдаланушы аты<input name="username" autoComplete="username" required maxLength={150}/></label>
    <label>Құпиясөз<input name="password" type="password" autoComplete="current-password" required/></label>
  </Form>;
}
