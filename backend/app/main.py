from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
from enum import Enum
import json
import os
from pathlib import Path
import re

# Pydantic models
class ContractType(str, Enum):
    RENT = "rent_contract"
    SERVICE = "service_contract"
    NDA = "nda_contract"
    LOAN = "loan_contract"

class ContractField(BaseModel):
    id: str
    label: str
    type: str
    required: bool = True
    options: Optional[List[Dict[str, str]]] = None
    validation: Optional[Dict[str, Any]] = None
    conditional: Optional[Dict[str, Any]] = None

class ContractTemplate(BaseModel):
    id: str
    title: str
    description: str
    fields: List[ContractField]
    template: Dict[str, Any]

class ContractData(BaseModel):
    contract_type: ContractType
    form_data: Dict[str, Any]

class GeneratedContract(BaseModel):
    contract_type: str
    title: str
    content: str
    generated_at: datetime

# FastAPI app
app = FastAPI(
    title="Document AI API",
    description="AI-powered legal document constructor API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
TEMPLATES_DIR = Path(__file__).parent / "templates"
_contract_templates: Dict[str, ContractTemplate] = {}

def load_templates():
    """Load all contract templates from JSON files"""
    global _contract_templates
    
    for template_file in TEMPLATES_DIR.glob("*.json"):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                template = ContractTemplate(**data)
                _contract_templates[template.id] = template
        except Exception as e:
            print(f"Error loading template {template_file}: {e}")

def validate_field_value(field: ContractField, value: Any) -> tuple[bool, Optional[str]]:
    """Validate a field value against its validation rules"""
    
    # Check required fields
    if field.required and (value is None or value == ""):
        return False, f"Field '{field.label}' is required"
    
    # Skip validation for empty optional fields
    if not field.required and (value is None or value == ""):
        return True, None
    
    # Get validation rules
    validation = field.validation or {}
    
    # Type-specific validations
    if field.type == "text":
        if not isinstance(value, str):
            return False, f"Field '{field.label}' must be text"
        
        if "min_length" in validation and len(value) < validation["min_length"]:
            return False, f"Field '{field.label}' must be at least {validation['min_length']} characters"
        
        if "max_length" in validation and len(value) > validation["max_length"]:
            return False, f"Field '{field.label}' must be no more than {validation['max_length']} characters"
        
        if "pattern" in validation and not re.match(validation["pattern"], value):
            return False, f"Field '{field.label}' format is invalid"
    
    elif field.type in ["number", "money"]:
        try:
            num_value = float(value)
            
            if "min" in validation and num_value < validation["min"]:
                return False, f"Field '{field.label}' must be at least {validation['min']}"
            
            if "max" in validation and num_value > validation["max"]:
                return False, f"Field '{field.label}' must be no more than {validation['max']}"
                
        except (ValueError, TypeError):
            return False, f"Field '{field.label}' must be a valid number"
    
    elif field.type == "date":
        try:
            if isinstance(value, str):
                date_value = datetime.fromisoformat(value.replace('Z', '+00:00')).date()
            elif isinstance(value, date):
                date_value = value
            else:
                return False, f"Field '{field.label}' must be a valid date"
            
            if "future_date" in validation and validation["future_date"]:
                if date_value <= date.today():
                    return False, f"Field '{field.label}' must be a future date"
                    
        except (ValueError, TypeError):
            return False, f"Field '{field.label}' must be a valid date"
    
    elif field.type == "phone":
        if not isinstance(value, str):
            return False, f"Field '{field.label}' must be text"
        
        if "pattern" in validation and not re.match(validation["pattern"], value):
            return False, f"Field '{field.label}' must be a valid phone number"
    
    elif field.type == "email":
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            return False, f"Field '{field.label}' must be a valid email address"
    
    return True, None

def process_template_content(content: str, data: Dict[str, Any]) -> str:
    """Process template content with simple variable substitution"""
    
    # Define value mappings
    value_mappings = {
        'payment_schedule': {
            'full': 'одноразово в повному обсязі до закінчення терміну',
            'monthly': 'щомісячно рівними частинами',
            'quarterly': 'щоквартально рівними частинами'
        },
        'payment_method': {
            'cash': 'готівка',
            'bank_transfer': 'банківський переказ',
            'card': 'картка'
        }
    }
    
    # Simple variable substitution
    for key, value in data.items():
        placeholder = f"{{{{{key}}}}}"
        if placeholder in content:
            # Convert boolean values to Ukrainian text
            if isinstance(value, bool):
                value = "так" if value else "ні"
            # Apply mappings if available
            elif key in value_mappings and str(value) in value_mappings[key]:
                value = value_mappings[key][str(value)]
            content = content.replace(placeholder, str(value))
    
    # Handle simple conditional blocks
    import re
    
    # Handle {{#if field}}true_text{{else}}false_text{{/if}} blocks
    def replace_if_block(match):
        condition = match.group(1)
        full_content = match.group(2)
        
        # Split by {{else}} if it exists
        if "{{else}}" in full_content:
            true_content, false_content = full_content.split("{{else}}", 1)
        else:
            true_content = full_content
            false_content = ""
        
        # Evaluate condition
        condition_value = data.get(condition, False)
        if condition_value:
            return true_content.strip()
        else:
            return false_content.strip()
    
    # Pattern for {{#if condition}}content{{/if}}
    if_pattern = r'{{#if\s+(\w+)}}(.*?){{/if}}'
    content = re.sub(if_pattern, replace_if_block, content, flags=re.DOTALL)
    
    # Handle {{#eq field 'value'}} blocks
    def replace_eq_block(match):
        field = match.group(1)
        expected_value = match.group(2).strip("'\"")
        block_content = match.group(3)
        
        field_value = data.get(field, "")
        if str(field_value) == expected_value:
            return block_content
        else:
            return ""
    
    # Pattern for {{#eq field 'value'}}content{{/eq}}
    eq_pattern = r'{{#eq\s+(\w+)\s+[\'"]([^\'"]*)[\'"]}}(.*?){{/eq}}'
    content = re.sub(eq_pattern, replace_eq_block, content, flags=re.DOTALL)
    
    return content

# Initialize templates on startup
@app.on_event("startup")
async def startup_event():
    load_templates()

@app.get("/")
async def root():
    return {"message": "Document AI API is running", "version": "1.0.0"}

@app.get("/contracts/types", response_model=List[Dict[str, str]])
async def get_contract_types():
    """Get all available contract types"""
    return [
        {"id": template_id, "title": template.title, "description": template.description}
        for template_id, template in _contract_templates.items()
    ]

@app.get("/contracts/{contract_type}/template", response_model=ContractTemplate)
async def get_contract_template(contract_type: ContractType):
    """Get template for a specific contract type"""
    if contract_type.value not in _contract_templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract template '{contract_type.value}' not found"
        )
    
    return _contract_templates[contract_type.value]

@app.post("/contracts/validate")
async def validate_contract_data(contract_data: ContractData):
    """Validate contract form data against template rules"""
    
    template = _contract_templates.get(contract_data.contract_type.value)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract template '{contract_data.contract_type.value}' not found"
        )
    
    errors = []
    
    for field in template.fields:
        # Check conditional fields
        if field.conditional:
            condition_field = field.conditional.get("field")
            condition_value = field.conditional.get("value")
            
            if condition_field in contract_data.form_data:
                actual_value = contract_data.form_data[condition_field]
                if actual_value != condition_value:
                    continue  # Skip validation for conditional field that shouldn't be shown
        
        # Validate field value
        value = contract_data.form_data.get(field.id)
        is_valid, error_message = validate_field_value(field, value)
        
        if not is_valid:
            errors.append({
                "field": field.id,
                "message": error_message
            })
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

@app.post("/contracts/generate", response_model=GeneratedContract)
async def generate_contract(contract_data: ContractData):
    """Generate a contract document from form data"""
    
    template = _contract_templates.get(contract_data.contract_type.value)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract template '{contract_data.contract_type.value}' not found"
        )
    
    # Validate data first
    validation_result = await validate_contract_data(contract_data)
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Validation failed", "errors": validation_result["errors"]}
        )
    
    # Add current date to form data
    form_data = contract_data.form_data.copy()
    form_data["current_date"] = datetime.now().strftime("%d.%m.%Y")
    
    # Generate contract content
    contract_content = []
    
    # Add title
    title = template.template.get("title", template.title)
    contract_content.append(f"**{title}**\n")
    
    # Process sections
    sections = template.template.get("sections", [])
    for section in sections:
        section_title = section.get("title", "")
        section_content = section.get("content", "")
        
        # Process template variables in content
        processed_content = process_template_content(section_content, form_data)
        
        contract_content.append(f"\n## {section_title}\n")
        contract_content.append(f"{processed_content}\n")
    
    # Add signatures
    signatures = template.template.get("signatures", [])
    if signatures:
        contract_content.append("\n## ПІДПИСИ\n")
        for signature in signatures:
            party = process_template_content(signature.get("party", ""), form_data)
            signature_line = process_template_content(signature.get("signature_line", ""), form_data)
            contract_content.append(f"{party}: {signature_line}\n")
    
    # Add footer
    footer = template.template.get("footer", "")
    if footer:
        processed_footer = process_template_content(footer, form_data)
        contract_content.append(f"\n---\n{processed_footer}")
    
    final_content = "".join(contract_content)
    
    return GeneratedContract(
        contract_type=contract_data.contract_type.value,
        title=template.title,
        content=final_content,
        generated_at=datetime.now()
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "templates_loaded": len(_contract_templates)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)