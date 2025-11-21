import os
import json
import boto3
import base64

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import markdown
from weasyprint import HTML

# ------------------- AWS -------------------
boto3.setup_default_session()
bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION", "eu-central-1"))
s3 = boto3.client("s3")

S3_BUCKET = os.getenv("S3_KNOWLEDGE_BUCKET")  # ← твій бакет з законами/шаблонами
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
    content_pdf_base64: str | None = None
    generated_at: datetime

# ------------------- RAG з S3 -------------------
# def get_rag_context() -> str:
#     if not S3_BUCKET:
#         return "Актуальне законодавство України 2025 року."

#     try:
#         objects = s3.list_objects_v2(Bucket=S3_BUCKET, MaxKeys=10)
#         texts = []
#         for obj in objects.get("Contents", []):
#             key = obj["Key"]
#             if key.lower().endswith((".txt", ".md", ".pdf")):
#                 data = s3.get_object(Bucket=S3_BUCKET, Key=key)
#                 content = data["Body"].read().decode("utf-8", errors="ignore")
#                 texts.append(f"--- {key} ---\n{content[:7000]}")
#         return "\n\n".join(texts)[:28_000]
#     except Exception as e:
#         print("S3 RAG error:", e)
#         return "Актуальне законодавство України 2025 року."

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
@app.get("/contracts/types")
def get_types():
    return [{"id": k, "title": v} for k, v in CONTRACTS.items()]

@app.post("/contracts/generate", response_model=GenerateResponse)
async def generate_contract(req: GenerateRequest):
    if req.contract_type not in CONTRACTS:
        raise HTTPException(404, "Тип договору не знайдено")

    answers = req.form_data.copy()
    answers["current_date"] = datetime.now().strftime("%d.%m.%Y")

    rag = get_rag_context()

    system_prompt = "Ти — найкращий український юрист 2025 року. Генеруєш тільки чистий текст договору українською мовою без пояснень."

#     user_prompt = f"""
# Тип договору: {CONTRACTS[req.contract_type]}

# Дані користувача:
# {json.dumps(answers, ensure_ascii=False, indent=2)}

# База знань (закони, шаблони):
# {rag}

# Згенеруй повний юридично правильний договір у форматі Markdown.
# Місце укладення — м. Київ. Суми — прописом.
# """
    user_prompt = f"""
        ТИ — найкращий український корпоративний юрист 2025 року.  
        Ти створюєш ТІЛЬКИ повний, юридично бездоганний договір українською мовою у форматі Markdown.  
        Жодних пояснень, коментарів, вибачень чи вступів — тільки чистий текст договору.

        Тип договору: {CONTRACTS[req.contract_type]}

        Дані для заповнення:
        {json.dumps(answers, ensure_ascii=False, indent=2)}

        Поточна дата: {answers.get("current_date", datetime.now().strftime("%d.%m.%Y"))}

        Вимоги, які ти зобов’язаний виконати 100%:
        1. Місце укладення — завжди м. Київ
        2. Повна назва договору великими літерами посередині
        3. Номер договору не потрібен
        4. Повні реквізити сторін на початку та в кінці
        5. ВСІ суми обов’язково прописом українською (наприклад: 50 000 грн — п’ятдесят тисяч гривень 00 копійок)
        6. Всі дати — і цифрами, і прописом
        7. Повний набір обов’язкових розділів для цього типу договору (предмет, строк, права та обов’язки, відповідальність, штрафні санкції, форс-мажор, порядок зміни та розірвання, реквізити та підписи)
        8. Для NDA обов’язково: визначення конфіденційної інформації, строк дії (в роках від дати підписання), штраф за порушення, юрисдикція України
        9. Для оренди: застава, комунальні платежі, стан квартири, акт приймання-передачі
        10. Для позики: відсотки або безвідсоткова, графік повернення (якщо є), пеня за прострочення
        11. Для послуг ФОП: акт виконаних робіт, порядок здачі-приймання, гарантії

        Згенеруй ПОВНИЙ договір «під ключ», готовий до підписання через Дія.Підпис.
        Використовуй офіційно-діловий стиль, без водяності.
    """

    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": 0.5,
                "top_p": 0.9,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            })
        )

        result = json.loads(response["body"].read())
        text = result["content"][0]["text"].strip()

                # ───── ФІНАЛЬНИЙ КРАСИВИЙ PDF, ЯКИЙ НІКОЛИ НЕ ВИЛАЗИТЬ ЗА А4 ─────
        html_content = markdown.markdown(text, extensions=['extra', 'tables', 'nl2br'])

        full_html = f"""<!DOCTYPE html>
        <html lang="uk">
        <head>
            <meta charset="UTF-8">
            <title>{CONTRACTS[req.contract_type]}</title>
            <style>
                @page {{
                    size: A4;
                    margin: 20mm 15mm 25mm 18mm;
                    @bottom-center {{ content: "Сторінка " counter(page); font-size: 10pt; color: #666; }}
                    @bottom-right  {{ content: "Дія.Договір AI • {datetime.now().strftime("%d.%m.%Y")}"; font-size: 9pt; color: #999; }}
                }}
                body {{
                    font-family: "Times New Roman", "DejaVu Serif", serif;
                    font-size: 12pt;
                    line-height: 1.5;
                    color: #000;
                    margin: 0;
                    padding: 0;
                }}
                h1 {{ font-size: 16pt; text-align: center; text-transform: uppercase; margin: 30pt 0 20pt 0; font-weight: bold; }}
                h2 {{ font-size: 13pt; margin: 20pt 0 10pt 0; font-weight: bold; }}
                p {{ margin: 0 0 10pt 0; text-align: justify; text-indent: 30pt; }}
                p.noindent {{ text-indent: 0; }}
                p.center {{ text-align: center; text-indent: 0; }}
                ul, ol {{ margin: 8pt 0; padding-left: 40pt; }}
                table {{ width: 100%; border-collapse: collapse; margin: 12pt 0; }}
                td, th {{ border: 1px solid #000; padding: 6pt; vertical-align: top; }}
                .signature {{
                    margin-top: 50pt;
                    display: flex;
                    justify-content: space-between;
                    font-size: 12pt;
                }}
                .signature div {{
                    width: 48%;
                    border-top: 1px solid #000;
                    padding-top: 8pt;
                    text-align: center;
                }}
                .small {{ font-size: 10pt; color: #555; text-align: center; margin-top: 30pt; }}
            </style>
        </head>
        <body>
            {html_content}
            
            <div class="signature">
                <div>Розкриваюча сторона<br>{answers.get("disclosing_party_name", "______________________")}</div>
                <div>Отримуюча сторона<br>{answers.get("receiving_party_name", "______________________")}</div>
            </div>
            <p class="small">Договір підписано кваліфікованим електронним підписом через Дія.Підпис</p>
        </body>
        </html>"""

        pdf_bytes = HTML(string=full_html, base_url=".").write_pdf(
            stylesheets=[
                # примусово ламаємо довгі слова і не даємо таблицям/рядкам вилазити
                "body { word-wrap: break-word; overflow-wrap: break-word; }"
            ]
        )
        pdf_b64 = base64.b64encode(pdf_bytes).decode()    
    
        # PDF
        # html = markdown.markdown(text)
        # styled = f"<html><head><meta charset='utf-8'></head><body style='font-family: Arial; padding: 40px;'>{html}</body></html>"
        # pdf_bytes = HTML(string=styled).write_pdf()
        # pdf_b64 = base64.b64encode(pdf_bytes).decode()

        return GenerateResponse(
            contract_type=req.contract_type,
            title=CONTRACTS[req.contract_type],
            content_markdown=text,
            content_pdf_base64=pdf_b64,
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(500, f"Bedrock error: {str(e)}")

@app.get("/health")
def health():
    return {"status": "OK", "ai": "bedrock-claude-3.5-sonnet", "s3": bool(S3_BUCKET)}