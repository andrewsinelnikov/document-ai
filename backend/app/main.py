import os
import json
import boto3
import base64
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import markdown
from weasyprint import HTML, CSS
import textwrap
# ------------------- AWS -------------------
boto3.setup_default_session()
bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION", "eu-central-1"))
s3 = boto3.client("s3")
S3_BUCKET = os.getenv("S3_KNOWLEDGE_BUCKET") # ← твій бакет з законами/шаблонами
# MODEL_ID = os.getenv("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
MODEL_ID = os.getenv("BEDROCK_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0")
# ------------------- FastAPI -------------------
app = FastAPI(title="Дія.Договір AI (Bedrock + S3)", version="2.0")
app.add_middleware(
    CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)
# ------------------- Договори -------------------
CONTRACTS = {
"rent_contract": "Договір оренди квартири",
"loan_contract": "Договір позики між фізичними особами",
"nda_contract": "Угода про нерозголошення (NDA)",
"service_contract": "Договір надання послуг (ФОП)",
}
class GenerateRequest(BaseModel):
    contract_type: str
    form_data: Dict[str, Any]
    
class GenerateResponse(BaseModel):
    contract_type: str
    title: str
    content_markdown: str
    content_html: str           
    content_pdf_base64: str     
    generated_at: datetime
    
# ------------------- RAG з S3 -------------------
# def get_rag_context() -> str:
# if not S3_BUCKET:
# return "Актуальне законодавство України 2025 року."
# try:
# objects = s3.list_objects_v2(Bucket=S3_BUCKET, MaxKeys=10)
# texts = []
# for obj in objects.get("Contents", []):
# key = obj["Key"]
# if key.lower().endswith((".txt", ".md", ".pdf")):
# data = s3.get_object(Bucket=S3_BUCKET, Key=key)
# content = data["Body"].read().decode("utf-8", errors="ignore")
# texts.append(f"--- {key} ---\n{content[:7000]}")
# return "\n\n".join(texts)[:28_000]
# except Exception as e:
# print("S3 RAG error:", e)
# return "Актуальне законодавство України 2025 року."
def get_rag_context() -> str:
# Для хакатону відключаємо S3 — модель і так знає закони
    return """
        Актуальне законодавство України станом на 2025 рік:
        • Цивільний кодекс України (редакція 2024–2025)
        • Житловий кодекс України
        • Закон України «Про оренду житла»
        • Закон України «Про електронні довірчі послуги» (Дія.Підпис)
        • Податковий кодекс (ФОП 3 група)
        • Закон про захист персональних даних
        • Стандартні шаблони договорів з реєстру Мін'юсту та Ліга:Закон
    """
# ------------------- Ендпоінти -------------------

@app.post("/contracts/generate", response_model=GenerateResponse)
async def generate_contract(req: GenerateRequest):
    if req.contract_type not in CONTRACTS:
        raise HTTPException(404, "Тип договору не знайдено")

    answers = req.form_data.copy()
    answers["current_date"] = datetime.now().strftime("%d.%m.%Y")

    rag = get_rag_context()

    system_prompt = "Ти — найкращий український юрист року. Генеруєш тільки чистий текст договору українською мовою без пояснень."
    
    user_prompt = f"""
    ТИ — найкращий український юрист-контрактник року. Згенеруй ПОВНИЙ юридично коректний договір українською у форматі Markdown.

    Тип: {CONTRACTS[req.contract_type]}
    Дата: {answers["current_date"]}
    Місце: м. Київ

    Дані:
    {json.dumps(answers, ensure_ascii=False, indent=2)}

    ОБОВ’ЯЗКОВО:
    1. Договір має бути мінімум 3000 символів.
    2. Обов’язково присутні розділи:
        1. Предмет договору
        2. Права та обов’язки сторін
        3. Строк дії договору
        4. Конфіденційна інформація / Опис послуг / Порядок оплати
        5. Відповідальність сторін
        6. Форс-мажор
        7. Порядок зміни та розірвання
        8. Інші умови
        9. Реквізити та підписи сторін
    3. ВСІ суми — і цифрами, і прописом українською.
    4. Всі дати — і цифрами, і прописом.
    5. Для NDA — чітке визначення конфіденційної інформації, строк дії після завершення, штраф ≥100000 грн.
    6. В кінці — блоки для підписів.

    Пиши ТІЛЬКИ чистий Markdown без коментарів, вступів і пояснень.
    """

    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": 0.3,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            })
        )

        result = json.loads(response["body"].read())
        markdown_text = result["content"][0]["text"].strip()

        # === КОНВЕРТАЦІЯ Markdown → HTML ===
        html_body = markdown.markdown(
            markdown_text,
            extensions=['extra', 'tables', 'nl2br', 'sane_lists', 'toc']
        )

        # === ПОВНИЙ ШАБЛОН HTML ДЛЯ КРАСИВОГО ДОГОВОРУ ===
        full_html = f"""<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="utf-8">
    <title>{CONTRACTS[req.contract_type]}</title>
    <style>
        @page {{ size: A4; margin: 2cm 2.5cm; }}
        body {{
            font-family: 'Times New Roman', serif;
            font-size: 14pt;
            line-height: 1.65;
            color: black;
        }}
        h1 {{
            text-align: center;
            text-transform: uppercase;
            font-size: 18pt;
            margin: 2cm 0 1.5cm;
            font-weight: bold;
        }}
        h2 {{
            font-size: 15pt;
            margin: 1.8em 0 0.8em;
            font-weight: bold;
        }}
        p {{
            text-indent: 3.5rem;
            text-align: justify;
            margin: 0 0 1em;
        }}
        p.noindent {{ text-indent: 0; }}
        ul, ol {{ margin: 1em 0; padding-left: 4rem; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5em 0;
        }}
        td, th {{
            border: 1px solid black;
            padding: 8px;
            vertical-align: top;
        }}
        .signature {{
            margin-top: 100px;
            display: flex;
            justify-content: space-between;
            font-size: 14pt;
        }}
        .signature div {{
            width: 45%;
            text-align: center;
        }}
        .signature .line {{
            border-top: 1px solid black;
            margin-top: 50px;
            padding-top: 10px;
        }}
        .footer {{
            margin-top: 80px;
            text-align: center;
            font-size: 12pt;
            color: #555;
        }}
    </style>
</head>
<body>
    {html_body}
    <div class="signature">
        <div>
            <div>Перша сторона</div>
            <div class="line">______________________</div>
            <div>(підпис та ПІБ)</div>
        </div>
        <div>
            <div>Друга сторона</div>
            <div class="line">______________________</div>
            <div>(підпис та ПІБ)</div>
        </div>
    </div>
    <div class="footer">
        Договір підписано кваліфікованим електронним підписом через Дія.Підпис<br>
        {datetime.now().strftime("%d.%m.%Y %H:%M")}
    </div>
</body>
</html>"""

        # === Генерація PDF ===
        pdf_bytes = HTML(string=full_html).write_pdf()
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        return GenerateResponse(
            contract_type=req.contract_type,
            title=CONTRACTS[req.contract_type],
            content_markdown=markdown_text,
            content_html=full_html,           # для веб-прев’ю
            content_pdf_base64=pdf_base64,    # одразу готово!
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(500, f"Помилка генерації: {str(e)}")


@app.get("/health")
def health(): 
    return {"status": "OK", "ai": "bedrock-claude-3.5-sonnet", "s3": bool(S3_BUCKET)}

