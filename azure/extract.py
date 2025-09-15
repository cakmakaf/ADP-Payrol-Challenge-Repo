import os
from typing import Dict, Any
import json
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.models import AnalyzeResult
from openai import AzureOpenAI

# Azure Clients (use env vars for auth)
document_intelligence_client = DocumentIntelligenceClient(
    endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"))
)

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview"
)

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Preprocess: Use Azure Document Intelligence to extract text from PDF."""
    poller = document_intelligence_client.begin_analyze_document(
        "prebuilt-layout",  # Model for layout/text extraction
        analyze_request={"url": None},  # Local bytes
        content_type="application/pdf",
        bytes_source=pdf_bytes  # Pass PDF bytes
    )
    result: AnalyzeResult = poller.result()
    text = ''
    for page in result.pages:
        for line in page.lines:
            text += line.content + '\n'
    return text.strip()

def extract_structured_data(text: str) -> Dict[str, Any]:
    """LLM Extraction: Use Azure OpenAI (GPT) with prompt engineering to parse JSON."""
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
    
    response = openai_client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),  # e.g., "gpt-35-turbo"
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,  # Low for structured output
        max_tokens=1000
    )
    extracted_json = json.loads(response.choices[0].message.content)
    return extracted_json

def validate_extraction(extracted: Dict[str, Any], golden: Dict[str, Any] = None) -> Dict[str, float]:
    """Optional Eval: Simple field-level accuracy."""
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
            accuracy[key] = 1.0 if str(extracted[key]).lower() == str(golden[key]).lower() else 0.0
    
    overall_precision = sum(accuracy.values()) / len(accuracy)
    return {"overall_accuracy": overall_precision, "field_accuracies": accuracy}