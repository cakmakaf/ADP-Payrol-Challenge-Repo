import streamlit as st
import io
from extract import extract_text_from_pdf, extract_structured_data, validate_extraction
import json

st.title("W-2 Document Extraction Prototype (Azure)")

uploaded_file = st.file_uploader("Upload W-2 PDF", type="pdf")

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    text = extract_text_from_pdf(pdf_bytes)
    st.text_area("Extracted Text (Preview)", text, height=200)
    
    with st.spinner("Extracting structured data..."):
        extracted = extract_structured_data(text)
    
    st.subheader("Extracted JSON")
    st.json(extracted)
    
    # Optional Validation
    if st.checkbox("Validate against Golden Sample"):
        with open("golden_sample.json", "r") as f:
            golden = json.load(f)
        validation = validate_extraction(extracted, golden)
        st.subheader("Validation Results")
        st.json(validation)

# Download Sample
if st.button("Download Sample W-2 PDF"):
    import requests
    url = "https://support.adp.com/adp_payroll/content/hybrid/PDF/W2_Interactive.pdf"
    response = requests.get(url)
    st.download_button("Download", response.content, "sample_w2.pdf", "application/pdf")