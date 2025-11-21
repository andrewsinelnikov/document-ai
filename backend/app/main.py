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

    system_prompt = "Ти — найкращий український юрист року. Генеруєш тільки чистий текст договору українською мовою без пояснень."
    user_prompt = f"""
        ТИ — найкращий український юрист-контрактник року. Твоя єдина задача — згенерувати ПОВНИЙ, юридично бездоганний договір українською мовою у форматі Markdown.

        Тип договору: {CONTRACTS[req.contract_type]}
        Дата укладення: {answers.get("current_date", datetime.now().strftime("%d.%m.%Y"))}
        Місце укладення: м. Київ

        Дані сторін та умови:
        {json.dumps(answers, ensure_ascii=False, indent=2)}

        ОБОВ’ЯЗКОВІ ВИМОГИ — ВИКОНАЙ ВСІ БЕЗ ВИНЯТКУ:
        1. Договір має бути мінімум 3000 символів (це ≈5–7 сторінок А4)
        2. Обов’язково присутні розділи (кожен з номером і назвою):
        1. Предмет договору
        2. Права та обов’язки сторін
        3. Строк дії договору
        4. Конфіденційна інформація (для NDA) / Опис послуг (для послуг) / Порядок оплати та розрахунків
        5. Відповідальність сторін
        6. Обставини непереборної сили (форс-мажор)
        7. Порядок зміни та розірвання договору
        8. Інші умови
        9. Реквізити та підписи сторін
        3. ВСІ суми — і цифрами, і прописом українською мовою
        4. Всі дати — і цифрами, і прописом
        5. Для NDA обов’язково: чітке визначення конфіденційної інформації, строк дії після припинення співпраці, штраф за кожне порушення (не менше 100 000 грн), заборона передачі третім особам
        6. В кінці — таблиця або блоки з реквізитами сторін і місця для підписів

        Пиши ТІЛЬКИ чистий Markdown договору. Жодних пояснень, вибачень, вступів чи висновків — тільки текст договору від першої до останньої літери.

        Якщо не виконаєш всі пункти — тебе звільнять з посади головного юриста України.
    """
    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": 0.5,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            })
        )

        result = json.loads(response["body"].read())
        markdown_text = result["content"][0]["text"].strip()

        # 1. Генеруємо красивий HTML для веб-прев'ю
        html_content = markdown.markdown(
            markdown_text,
            extensions=['extra', 'tables', 'nl2br', 'sane_lists']
        )

        # Додаємо підписи та футер
        full_html = f"""
        <!DOCTYPE html>
        <html lang="uk"><head><meta charset="utf-8">
        <style>
            body {{ font-family: 'Times New Roman', serif; font-size: 14pt; line-height: 1.65; padding: 40px 60px; background: white; color: black; }}
            h1 {{ text-align: center; text-transform: uppercase; font-size: 20pt; margin: 40px 0 50px; font-weight: bold; }}
            h2 {{ font-size: 15pt; margin: 30px 0 15px; font-weight: bold; }}
            p {{ text-indent: 3.5rem; text-align: justify; margin: 0 0 12pt; }}
            ul, ol {{ margin: 12pt 0; padding-left: 4rem; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            td, th {{ border: 1px solid black; padding: 8px; word-break: break-word; }}
            .signature {{ margin-top: 80px; display: flex; justify-content: space-between; }}
            .signature div {{ width: 45%; text-align: center; border-top: 1px solid black; padding-top: 12px; }}
            .footer {{ text-align: center; font-size: 11pt; color: #555; margin-top: 60px; }}
        </style>
        </head><body>
            {html_content}
            <div class="signature">
                <div>Перша сторона<br>______________________</div>
                <div>Друга сторона<br>______________________</div>
            </div>
            <div class="footer">
                Договір підписано кваліфікованим електронним підписом через Дія.Підпис
            </div>
        </body></html>
        """

        return GenerateResponse(
            contract_type=req.contract_type,
            title=CONTRACTS[req.contract_type],
            content_markdown=markdown_text,
            content_html=full_html,                    # ← для швидкого веб-прев'ю
            content_pdf_base64=None,                   # ← поки null
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(500, f"Bedrock error: {str(e)}")

@app.post("/contracts/to-pdf")
async def generate_pdf_endpoint(request: GenerateRequest):
    """Окремий ендпоінт — генерує PDF тільки коли користувач натиснув кнопку"""
    # Повторно генеруємо markdown (можна кешувати, але для простоти — повтор)
    # Або краще: передавай markdown_text у тілі запиту — ще швидше

    # Простий варіант — повторюємо генерацію (Claude швидко)
    result = await generate_contract(request)  # перевикористовуємо логіку
    markdown_text = result.content_markdown

    html_content = markdown.markdown(markdown_text, extensions=['extra', 'tables', 'nl2br', 'sane_lists'])
    
    full_html = f"""<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 20mm 16mm 25mm 16mm;
                @bottom-center {{ content: "Сторінка " counter(page); font-size: 10pt; color: #666; }}
            }}
            body {{ font-family: "Times New Roman", serif; font-size: 12pt; line-height: 1.6; }}
            h1 {{ text-align: center; text-transform: uppercase; font-size: 18pt; margin: 40mm 0 30mm; }}
            p {{ text-indent: 35pt; text-align: justify; margin: 0 0 12pt; }}
            table {{ width: 100%; table-layout: fixed; border-collapse: collapse; }}
            td, th {{ border: 1px solid black; padding: 8px; word-break: break-all; }}
            .signature {{ margin-top: 80mm; display: flex; justify-content: space-between; }}
            .signature div {{ width: 45%; border-top: 1px solid black; padding-top: 12px; text-align: center; }}
        </style></head><body>
        {html_content}
        <div class="signature"> ... </div>
        </body></html>"""

    pdf_bytes = HTML(string=full_html).write_pdf(
        stylesheets=[CSS(string="""
            * { word-break: break-word !important; overflow-wrap: break-word !important; }
            table, td, th { word-break: break-all !important; }
        """)]
    )

    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    return {"content_pdf_base64": pdf_b64, "title": result.title}

@app.get("/health")
def health():
    return {"status": "OK", "ai": "bedrock-claude-3.5-sonnet", "s3": bool(S3_BUCKET)}