#!/usr/bin/env python3
"""
PDF to Markdown parser using the Marker API.
"""
import os
import sys
import json
import requests
import traceback
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Import the PDF service response model
from tools.pdf.pdf_response_model import PdfServiceResponse

# Load environment variables
load_dotenv(override=True)


def parse_pdf(
    pdf_path: str,
    page_range: Optional[str] = None,
    languages: Optional[str] = None,
    force_ocr: bool = False,
    paginate_output: bool = False,
    output_format: str = "markdown",
    api_url: str = "http://192.168.8.104:8001"
) -> PdfServiceResponse:
    """
    Convert a PDF file to markdown using the Marker API.
    
    Args:
        pdf_path: Path to the PDF file
        page_range: Page range to convert (comma separated page numbers or ranges, e.g., "0,5-10,20")
        languages: Comma separated list of languages for OCR
        force_ocr: Force OCR on all pages
        paginate_output: Whether to paginate the output
        output_format: Output format (markdown, json, or html)
        api_url: The base URL of the Marker API
    
    Returns:
        PdfServiceResponse object containing the conversion result
    """
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    endpoint = f"{api_url}/marker/upload"
    
    # Prepare the form data
    files = {"file": open(pdf_path, "rb")}
    data = {
        "page_range": page_range,
        "languages": languages,
        "force_ocr": str(force_ocr).lower(),
        "paginate_output": str(paginate_output).lower(),
        "output_format": output_format
    }
    
    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}
    
    try:
        print(f"Parsing PDF: {pdf_path}")
        response = requests.post(endpoint, files=files, data=data)
        
        # Close the file
        files["file"].close()
        
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)
        
        result = response.json()
        # Parse the response using our PdfServiceResponse model
        return PdfServiceResponse.model_validate(result)
    
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        print(traceback.format_exc())
        sys.exit(1)
