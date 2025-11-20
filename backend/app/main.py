import os
import json
import boto3
import base64
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
MODEL_ID = os.getenv("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")

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
def get_rag_context() -> str:
    if not S3_BUCKET:
        return "Актуальне законодавство України 2025 року."

    try:
        objects = s3.list_objects_v2(Bucket=S3_BUCKET, MaxKeys=10)
        texts = []
        for obj in objects.get("Contents", []):
            key = obj["Key"]
            if key.lower().endswith((".txt", ".md", ".pdf")):
                data = s3.get_object(Bucket=S3_BUCKET, Key=key)
                content = data["Body"].read().decode("utf-8", errors="ignore")
                texts.append(f"--- {key} ---\n{content[:7000]}")
        return "\n\n".join(texts)[:28_000]
    except Exception as e:
        print("S3 RAG error:", e)
        return "Актуальне законодавство України 2025 року."

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

    user_prompt = f"""
Тип договору: {CONTRACTS[req.contract_type]}

Дані користувача:
{json.dumps(answers, ensure_ascii=False, indent=2)}

База знань (закони, шаблони):
{rag}

Згенеруй повний юридично правильний договір у форматі Markdown.
Місце укладення — м. Київ. Суми — прописом.
"""

    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": 0.2,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            })
        )

        result = json.loads(response["body"].read())
        text = result["content"][0]["text"].strip()

        # PDF
        html = markdown.markdown(text)
        styled = f"<html><head><meta charset='utf-8'></head><body style='font-family: Arial; padding: 40px;'>{html}</body></html>"
        pdf_bytes = HTML(string=styled).write_pdf()
        pdf_b64 = base64.b64encode(pdf_bytes).decode()

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