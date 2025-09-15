import os
import boto3
import json
from typing import Dict, Any

# AWS Clients (assume configured)
textract = boto3.client('textract', region_name='us-east-1')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Preprocess: Use Textract to extract text from PDF."""
    response = textract.detect_document_text(
        Document={'Bytes': pdf_bytes}
    )
    text = ''
    for block in response['Blocks']:
        if block['BlockType'] == 'LINE':
            text += block['Text'] + '\n'
    return text.strip()

def extract_structured_data(text: str) -> Dict[str, Any]:
    """LLM Extraction: Use Bedrock (Claude) with prompt engineering to parse JSON."""
    prompt = f"""
    You are an expert at extracting data from W-2 forms. Parse the following text and output ONLY valid JSON with these fields:
    {{
        "employee": {{
            "name": "str",
            "ssn": "str (masked, e.g., XXX-XX-XXXX)",
            "address": "str"
        }},
        "employer": {{
            "name": "str",
            "address": "str"
        }},
        "tax_year": "str",
        "earnings": {{
            "wages": "float (box 1)",
            "social_security_wages": "float (box 3)",
            "medicare_wages": "float (box 5)"
        }},
        "deductions": {{
            "federal_tax": "float (box 2)",
            "social_security_tax": "float (box 4)",
            "medicare_tax": "float (box 6)",
            "state_tax": "float (state section)"
        }},
        "net_pay_estimate": "float (wages - total withholdings)",
        "ytd_totals": {{
            "total_wages": "float",
            "total_withheld": "float"
        }}
    }}
    If a field is missing, use null. Be precise with numbers.

    Text: {text}
    """
    
    response = bedrock.invoke_model(
        modelId='anthropic.claude-v2',  # Or claude-3-sonnet for better accuracy
        body=json.dumps({
            'prompt': prompt,
            'max_tokens_to_sample': 1000,
            'temperature': 0.1  # Low for structured output
        }),
        contentType='application/json',
        accept='application/json'
    )
    result = json.loads(response['body'].read())
    extracted_json = json.loads(result['completion'])  # Parse LLM output as JSON
    return extracted_json

def validate_extraction(extracted: Dict[str, Any], golden: Dict[str, Any] = None) -> Dict[str, float]:
    """Optional Eval: Simple field-level accuracy (exact match for strings, abs diff <1% for floats)."""
    if not golden:
        return {"status": "No golden dataset provided"}
    
    accuracy = {}
    for key in extracted:
        if isinstance(extracted[key], dict):
            sub_acc = {}
            for subkey in extracted[key]:
                val = extracted[key][subkey]
                gold_val = golden[key][subkey]
                if isinstance(val, str):
                    sub_acc[subkey] = 1.0 if val.lower() == gold_val.lower() else 0.0
                elif isinstance(val, float):
                    sub_acc[subkey] = 1.0 if abs(val - gold_val) / gold_val < 0.01 else 0.0
                else:
                    sub_acc[subkey] = 0.0
            accuracy[key] = sum(sub_acc.values()) / len(sub_acc)
        else:
            # Handle top-level like tax_year
            accuracy[key] = 1.0 if str(extracted[key]).lower() == str(golden[key]).lower() else 0.0
    
    overall_precision = sum(accuracy.values()) / len(accuracy)  # Simple average
    return {"overall_accuracy": overall_precision, "field_accuracies": accuracy}