import requests
import json
from datetime import datetime, date
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8000"

def test_basic_endpoints():
    """Test basic API endpoints"""
    print("=== Testing Basic Endpoints ===")
    
    # Test root endpoint
    response = requests.get(f"{BASE_URL}/")
    print(f"Root endpoint: {response.status_code} - {response.json()}")
    
    # Test health endpoint
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health endpoint: {response.status_code} - {response.json()}")
    
    # Test contract types
    response = requests.get(f"{BASE_URL}/contracts/types")
    print(f"Contract types: {response.status_code}")
    if response.status_code == 200:
        types = response.json()
        print(f"Available contract types: {len(types)}")
        for contract_type in types:
            print(f"  - {contract_type['id']}: {contract_type['title']}")
    
    print()

def test_contract_template(contract_type: str):
    """Test getting a contract template"""
    print(f"=== Testing Template for {contract_type} ===")
    
    response = requests.get(f"{BASE_URL}/contracts/{contract_type}/template")
    print(f"Template endpoint: {response.status_code}")
    
    if response.status_code == 200:
        template = response.json()
        print(f"Template title: {template['title']}")
        print(f"Fields count: {len(template['fields'])}")
        print("Fields:")
        for field in template['fields']:
            required = "required" if field['required'] else "optional"
            print(f"  - {field['id']} ({field['type']}, {required}): {field['label']}")
    else:
        print(f"Error: {response.json()}")
    
    print()
    return response.json() if response.status_code == 200 else None

def test_validation(contract_type: str, test_data: Dict[str, Any]):
    """Test contract data validation"""
    print(f"=== Testing Validation for {contract_type} ===")
    
    payload = {
        "contract_type": contract_type,
        "form_data": test_data
    }
    
    response = requests.post(f"{BASE_URL}/contracts/validate", json=payload)
    print(f"Validation endpoint: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Validation result: {'Valid' if result['valid'] else 'Invalid'}")
        if not result['valid']:
            print("Errors:")
            for error in result['errors']:
                print(f"  - {error['field']}: {error['message']}")
    else:
        print(f"Error: {response.json()}")
    
    print()
    return response.json() if response.status_code == 200 else None

def test_generation(contract_type: str, test_data: Dict[str, Any]):
    """Test contract generation"""
    print(f"=== Testing Generation for {contract_type} ===")
    
    payload = {
        "contract_type": contract_type,
        "form_data": test_data
    }
    
    response = requests.post(f"{BASE_URL}/contracts/generate", json=payload)
    print(f"Generation endpoint: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Generated contract type: {result['contract_type']}")
        print(f"Title: {result['title']}")
        print(f"Generated at: {result['generated_at']}")
        print("Content preview (first 300 chars):")
        print(result['content'][:300] + "...")
    else:
        print(f"Error: {response.json()}")
    
    print()
    return response.json() if response.status_code == 200 else None

def main():
    """Main test function"""
    print("Starting Document AI Backend Tests")
    print("=" * 50)
    
    try:
        # Test basic endpoints
        test_basic_endpoints()
        
        # Test loan contract
        print("Testing Loan Contract")
        print("-" * 30)
        
        loan_template = test_contract_template("loan_contract")
        
        # Test data for loan contract
        loan_test_data = {
            "lender_name": "Іванов Іван Іванович",
            "lender_passport": "АМ123456",
            "lender_address": "м. Київ, вул. Хрещатик, 1",
            "lender_phone": "+380501234567",
            "borrower_name": "Петров Петро Петрович",
            "borrower_passport": "ВС789012",
            "borrower_address": "м. Київ, вул. Незалежності, 2",
            "borrower_phone": "+380507654321",
            "loan_amount": 50000,
            "interest_rate": 12.5,
            "loan_purpose": "Купівля автомобіля",
            "return_date": "2026-12-31",
            "payment_schedule": "monthly",
            "collateral_required": False,
            "collateral_description": ""
        }
        
        validation_result = test_validation("loan_contract", loan_test_data)
        
        if validation_result and validation_result['valid']:
            generation_result = test_generation("loan_contract", loan_test_data)
        
        # Test rent contract
        print("Testing Rent Contract")
        print("-" * 30)
        
        rent_template = test_contract_template("rent_contract")
        
        # Test data for rent contract
        rent_test_data = {
            "landlord_name": "Сидорова Анна Петрівна",
            "landlord_passport": "КР456789",
            "landlord_address": "м. Львів, вул. Свободи, 10",
            "landlord_phone": "+380671234567",
            "tenant_name": "Коваль Олег Васильович",
            "tenant_passport": "МТ654321",
            "tenant_address": "м. Харків, пр. Науки, 5",
            "tenant_phone": "+380509876543",
            "property_address": "м. Київ, вул. Лесі Українки, 15, кв. 25",
            "property_area": 65,
            "property_rooms": 2,
            "rent_amount": 15000,
            "deposit_amount": 15000,
            "utilities_included": False,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "payment_day": 5
        }
        
        validation_result = test_validation("rent_contract", rent_test_data)
        
        if validation_result and validation_result['valid']:
            generation_result = test_generation("rent_contract", rent_test_data)
        
        print("All tests completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server.")
        print("Make sure the server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()