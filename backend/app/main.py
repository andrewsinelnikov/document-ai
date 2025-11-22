import os
import json
import boto3
import base64
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import markdown
from weasyprint import HTML

# AWS Bedrock
boto3.setup_default_session()
bedrock = boto3.client("bedrock-runtime", region_name="eu-central-1")

# ОБОВ'ЯЗКОВО ЦЯ МОДЕЛЬ — працює в 2025 році!
MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

app = FastAPI(title="Дія.Договір AI", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ті ж типи, що й у тебе раніше
class ContractData(BaseModel):
    contract_type: str
    form_data: Dict[str, Any]

class GeneratedContract(BaseModel):
    contract_type: str
    title: str
    content_markdown: str
    content_html: str
    content_pdf_base64: str
    generated_at: datetime

# Ті ж назви договорів
CONTRACT_TITLES = {
    "rent_contract": "Договір оренди квартири",
    "loan_contract": "Договір позики між фізичними особами",
    "nda_contract": "Угода про нерозголошення (NDA)",
    "service_contract": "Договір надання послуг (ФОП)",
}

@app.get("/contracts/types")
def get_types():
    return [
        {"id": k, "title": v} for k, v in CONTRACT_TITLES.items()
    ]

@app.post("/contracts/generate")
async def generate_with_ai(data: ContractData):
    if data.contract_type not in CONTRACT_TITLES:
        raise HTTPException(404, "Тип договору не підтримується")

    answers = data.form_data.copy()
    answers["current_date"] = datetime.now().strftime("%d.%m.%Y")

    prompt = f"""
Ти — найкращий український юрист 2025 року.
Згенеруй ПОВНИЙ, юридично бездоганний договір українською мовою у форматі Markdown.

Тип договору: {CONTRACT_TITLES[data.contract_type]}
Місце укладення: м. Київ
Дата: {answers["current_date"]}

Дані:
{json.dumps(answers, ensure_ascii=False, indent=2)}

ОБОВ’ЯЗКОВО:
- Тільки чистий Markdown (без ```, без пояснень)
- Всі розділи: Предмет, Права та обов’язки, Строк дії, Оплата, Відповідальність, Форс-мажор, Розірвання, Реквізити та підписи
- Суми та дати — і цифрами, і прописом
- В кінці — блоки для підписів обох сторін
"""

    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": 0.3,
                "system": "Ти — експерт з українського права. Відповідай ТІЛЬКИ текстом договору у Markdown.",
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        result = json.loads(response["body"].read())
        markdown_text = result["content"][0]["text"].strip()

        # Генеруємо гарний HTML
        html_body = markdown.markdown(markdown_text, extensions=['extra', 'tables', 'nl2br'])
        full_html = f"""<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="utf-8">
    <title>{CONTRACT_TITLES[data.contract_type]}</title>
    <style>
        body {{ font-family: 'Times New Roman', serif; font-size: 14pt; line-height: 1.7; padding: 2cm; }}
        h1 {{ text-align: center; text-transform: uppercase; font-size: 18pt; margin: 2cm 0 1.5cm; }}
        h2 {{ font-weight: bold; margin: 1.5em 0 0.8em; }}
        p {{ text-indent: 3.5rem; text-align: justify; margin: 0 0 1em; }}
        .signature {{ margin-top: 120px; display: flex; justify-content: space-between; }}
        .signature div {{ width: 45%; text-align: center; }}
        .signature .line {{ border-top: 1px solid black; margin-top: 70px; padding-top: 10px; }}
        .footer {{ margin-top: 100px; text-align: center; color: #555; }}
    </style>
</head>
<body>
{html_body}
<div class="signature">
    <div>Перша сторона<br><div class="line">______________________</div></div>
    <div>Друга сторона<br><div class="line">______________________</div></div>
</div>
<div class="footer">
    Договір підписано кваліфікованим електронним підписом через Дія.Підпис<br>
    {datetime.now().strftime("%d.%m.%Y %H:%M")}
</div>
</body>
</html>"""

        # Генеруємо PDF
        pdf_bytes = HTML(string=full_html).write_pdf()
        pdf_b64 = base64.b64encode(pdf_bytes).decode()

        return GeneratedContract(
            contract_type=data.contract_type,
            title=CONTRACT_TITLES[data.contract_type],
            content_markdown=markdown_text,
            content_html=full_html,
            content_pdf_base64=pdf_b64,
            generated_at=datetime.now()
        )

    except Exception as e:
        print("ПОМИЛКА AI:", str(e))
        raise HTTPException(500, f"AI помилка: {str(e)}")

@app.get("/health")
def health():
    return {"status": "OK", "ai": "Claude 3.5 Sonnet", "model": MODEL_ID}