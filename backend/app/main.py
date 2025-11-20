import os
import json
import boto3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from botocore.exceptions import ClientError
import markdown
from weasyprint import HTML

# ==================== MODELS ====================
class ContractType(str):
    RENT = "rent_contract"
    SERVICE = "service_contract"
    NDA = "nda_contract"
    LOAN = "loan_contract"

class ContractData(BaseModel):
    contract_type: ContractType
    form_data: Dict[str, Any]

class GeneratedContract(BaseModel):
    contract_type: str
    title: str
    content_markdown: str
    content_pdf_base64: str | None = None
    generated_at: datetime

# ==================== FASTAPI APP ====================
app = FastAPI(title="Дія.Договір AI", version="2.0-MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== BEDROCK CLIENT ====================
bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION"))

# ==================== RAG (з S3 або локально) ====================
def get_knowledge_context() -> str:
    bucket = os.getenv("S3_KNOWLEDGE_BUCKET")
    if bucket:
        try:
            s3 = boto3.client("s3")
            objects = s3.list_objects_v2(Bucket=bucket, MaxKeys=15)
            texts = []
            for obj in objects.get("Contents", []):
                if obj["Key"].lower().endswith((".txt", ".md")):
                    data = s3.get_object(Bucket=bucket, Key=obj["Key"])
                    text = data["Body"].read().decode("utf-8")
                    texts.append(f"--- {obj['Key']} ---\n{text[:8000]}")
            return "\n\n".join(texts)[:30_000]
        except Exception as e:
            print("S3 RAG error:", e)

    # fallback — локальна папка knowledge
    path = Path(__file__).parent / "knowledge"
    if path.exists():
        texts = []
        for file in path.glob("*.txt"):
            texts.append(file.read_text(encoding="utf-8")[:8000])
        return "\n\n".join(texts)[:30_000]

    return "Актуальне законодавство України 2025 року (ЦКУ, ГКУ, Податковий кодекс)."

# ==================== ТИПИ ДОГОВОРІВ (тільки назви) ====================
CONTRACT_TITLES = {
    "rent_contract": "Договір оренди квартири",
    "service_contract": "Договір надання послуг (ФОП)",
    "nda_contract": "NDA (Угода про нерозголошення)",
    "loan_contract": "Договір позики між фізичними особами",
}

# ==================== ENDPOINTS ====================
@app.get("/contracts/types")
def get_types():
    return [
        {"id": k, "title": v} for k, v in CONTRACT_TITLES.items()
    ]

@app.post("/contracts/generate", response_model=GeneratedContract)
async def generate_contract(data: ContractData):
    contract_type = data.contract_type.value
    if contract_type not in CONTRACT_TITLES:
        raise HTTPException(status_code=404, detail="Тип договору не підтримується")

    answers = data.form_data.copy()
    answers["current_date"] = datetime.now().strftime("%d.%m.%Y")
    answers["current_date_full"] = datetime.now().strftime("%d листопада %Y року")

    knowledge = get_knowledge_context()

    system_prompt = (
        "Ти — юридичний експерт Міністерства цифрової трансформації України. "
        "Генеруєш тільки чистий текст договору українською мовою без жодних пояснень, вибачень чи приміток. "
        "Використовуй актуальні норми ЦКУ, ГКУ, Податкового кодексу станом на 2025 рік. "
        "Додавай всі необхідні розділи, суми прописом, місце укладання — м. Київ."
    )

    user_prompt = f"""
Тип договору: {CONTRACT_TITLES[contract_type]}

Дані для заповнення:
{json.dumps(answers, ensure_ascii=False, indent=2)}

Додаткова юридична база:
{knowledge}

Згенеруй повний юридично грамотний договір у форматі Markdown.
"""

    try:
        response = bedrock.invoke_model(
            modelId=os.getenv("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": 0.2,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            })
        )

        result = json.loads(response["body"].read())
        markdown_text = result["content"][0]["text"].strip()

        # Генерація PDF
        html = markdown.markdown(markdown_text, extensions=["tables", "nl2br"])
        styled_html = f"""
        <html><head><meta charset="utf-8"></head><body style="font-family: 'Times New Roman', serif; padding: 40px;">
        {html}
        </body></html>
        """
        pdf_bytes = HTML(string=styled_html).write_pdf()

        import base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode()

        return GeneratedContract(
            contract_type=contract_type,
            title=CONTRACT_TITLES[contract_type],
            content_markdown=markdown_text,
            content_pdf_base64=pdf_base64,
            generated_at=datetime.now()
        )

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS Bedrock error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка генерації: {str(e)}")

@app.get("/health")
def health():
    return {"status": "ready", "ai": "bedrock-claude-3.5"}