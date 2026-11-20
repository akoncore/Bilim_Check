import {api, navigate} from "../api";
import {Form, Hero} from "../components/ui";

export function Login() {
  async function register(values) {
    await api("/login/", {name: values.get("name"), grade: Number(values.get("grade"))});
    navigate("/home/");
  }
  return <div className="split">
    <Hero label="Математика диагностикасы" title="Математикадан деңгейіңді анықта">
      Өз сыныбыңа дейінгі есептерді шығарып, қай тақырыпты қайталау керегін біл.
    </Hero>
    <Form action={register} label="Жалғастыру">
      <h2>Тестке тіркелу</h2>
      <label>Аты-жөнің<input name="name" required maxLength={120} autoComplete="name" placeholder="Аты-жөніңді жаз"/></label>
      <label>Сыныбың<select name="grade" required defaultValue=""><option value="">Сыныпты таңда</option>
        {Array.from({length: 11}, (_, i) => <option key={i} value={i + 1}>{i + 1}-сынып</option>)}
      </select></label>
    </Form>
  </div>;
}
