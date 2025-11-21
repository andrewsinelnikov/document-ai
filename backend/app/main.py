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
                "top_p": 0.9,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            })
        )

        result = json.loads(response["body"].read())
        text = result["content"][0]["text"].strip()

                # ───── ФІНАЛЬНИЙ PDF — 100% НЕ ВИЛІЗАЄ ЗА ПОЛЯ (WeasyPrint 62.2 + правильний CSS) ─────
        
        # safe_lines = []
        # for line in text.splitlines():
        #     # Якщо рядок довший за 95 символів — ріжемо його
        #     if len(line) > 95 and ' ' not in line:
        #         safe_lines.extend(textwrap.wrap(line, width=95))
        #     else:
        #         safe_lines.append(line)
        # safe_text = "\n".join(safe_lines)

        # # КРОК 2: Markdown → HTML
        # html_content = markdown.markdown(safe_text, extensions=['extra', 'tables', 'nl2br'])

        # # КРОК 3: Шаблон з жорстким CSS
        # full_html = f"""<!DOCTYPE html>
        # <html lang="uk">
        # <head>
        #     <meta charset="UTF-8">
        #     <title>{CONTRACTS[req.contract_type]}</title>
        #     <style>
        #         @page {{
        #             size: A4;
        #             margin: 18mm 16mm 25mm 16mm;
        #             @bottom-center {{ content: "Сторінка " counter(page); font-size: 10pt; color: #666; }}
        #         }}
        #         body {{
        #             font-family: "Liberation Serif", "Times New Roman", serif;
        #             font-size: 12pt;
        #             line-height: 1.55;
        #             margin: 0;
        #             padding: 0;
        #         }}
        #         h1 {{ font-size: 18pt; text-align: center; text-transform: uppercase; margin: 30mm 0 20mm; }}
        #         p {{ text-indent: 35pt; text-align: justify; margin: 0 0 12pt 0; }}
        #         table {{ width: 100%; table-layout: fixed; border-collapse: collapse; }}
        #         td, th {{ border: 1px solid black; padding: 8pt; }}
        #         .signature {{ margin-top: 60mm; display: flex; justify-content: space-between; }}
        #         .signature div {{ width: 48%; border-top: 1px solid black; padding-top: 12pt; text-align: center; }}
        #     </style>
        # </head>
        # <body>
        #     {html_content}
        #     <div class="signature">
        #         <div>Перша сторона<br>_________________________</div>
        #         <div>Друга сторона<br>_________________________</div>
        #     </div>
        #     <p style="text-align:center; font-size:10pt; color:#555; margin-top:30mm;">
        #         Договір підписано кваліфікованим електронним підписом через Дія.Підпис
        #     </p>
        # </body>
        # </html>"""

        # # КРОК 4: Найголовніше — додатковий CSS, який ламає ВСЕ
        # pdf_bytes = HTML(string=full_html).write_pdf(
        #     stylesheets=[CSS(string="""
        #         * { 
        #             word-break: break-all !important; 
        #             overflow-wrap: break-word !important; 
        #             hyphens: auto !important;
        #         }
        #         table, td, th { table-layout: fixed !important; word-break: break-all !important; }
        #     """)]
        # )
        # pdf_b64 = base64.b64encode(pdf_bytes).decode()
    
        # PDF
        # html = markdown.markdown(text)
        # styled = f"<html><head><meta charset='utf-8'></head><body style='font-family: Arial; padding: 40px;'>{html}</body></html>"
        # pdf_bytes = HTML(string=styled).write_pdf()
        # pdf_b64 = base64.b64encode(pdf_bytes).decode()

        html_content = markdown.markdown(text, extensions=['extra', 'tables', 'nl2br'])
        
        final_html = f"""
        <div style="max-width: 100%; word-break: break-word;">
            {html_content}
        </div>
        """

        pdf_b64 = base64.b64encode(final_html.encode('utf-8')).decode()

        # return GenerateResponse(
        #     contract_type=req.contract_type,
        #     title=CONTRACTS.get(req.contract_type, "Договір"),
        #     content_markdown=text,
        #     content_pdf_base64=pdf_b64,  
        #     content_html=final_html
        #     generated_at=datetime.now()
        # )

        return GenerateResponse(
            contract_type=req.contract_type,
            title=CONTRACTS[req.contract_type],
            content_markdown=text,
            content_pdf_base64=pdf_b64,
        )

    except Exception as e:
        raise HTTPException(500, f"Bedrock error: {str(e)}")

@app.get("/health")
def health():
    return {"status": "OK", "ai": "bedrock-claude-3.5-sonnet", "s3": bool(S3_BUCKET)}