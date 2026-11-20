import {api} from "../api";
import {Form} from "./ui";

export function QuestionBank() {
  async function upload(values, form) {
    const file = values.get("file");
    if (file.size > 2_000_000) throw new Error("Файл 2 МБ-тан аспауы керек.");
    let bank;
    try { bank = JSON.parse((await file.text()).replace(/^\uFEFF/, "")); }
    catch { throw new Error("JSON файл форматы қате."); }
    const data = await api("/admin/questions/import/", bank);
    form.reset();
    return `${data.imported} есеп сақталды.`;
  }
  return <Form action={upload} label="Импорттау">
    <h2>Есептерді жүктеу</h2>
    <p className="muted">JSON файлына сыныпты, тақырыпты, тапсырманы, жауап нұсқаларын және дұрыс жауаптың нөлден басталатын индексін енгізіңіз.</p>
    <label>JSON файл<input type="file" name="file" accept=".json,application/json" required/></label>
  </Form>;
}
