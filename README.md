# Договір AI

**AI-конструктор юридичних документів**  
Генерує юридично грамотні договори за 5 хвилин через інтерактивний чат.

[![Demo](docs/demo.gif)](https://document-ai.app)

---

## Опис
- Користувач обирає тип договору (оренда, ФОП, NDA)
- Проходить коротке опитування
- Отримує готовий `.docx` або `.pdf`
- Інтеграція з Diia.Підпис (mock)

**Для громадян. Без юриста. Через Дію.**

---

## Демо
![Demo](docs/demo.gif)

---

## Запуск

```bash
git clone https://github.com/andrewsinelnikov/document-ai.git
cd dogovir-za-khvylyn
pip install -r requirements.txt
streamlit run app/main.py
