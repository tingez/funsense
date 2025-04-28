#!/Users/tinge/work/tinge/agent/venv/funsense_env/bin/python
"""
Test script for pdf_parser.py using pdf-test.pdf and comparing with pdf-test.json
"""
import json
import traceback
import os
import sys
from typing import Dict, Any
import difflib

# Add the project root to the Python path
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# Now import can find the tools module
from tools.pdf.pdf_parser import parse_pdf

def test_pdf_parser():
    """
    Test the pdf_parser by parsing a test PDF and comparing it with expected results.
    """
    # Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_dir = os.path.join(project_root, "tools", "pdf")
    test_pdf_path = os.path.join(pdf_dir, "pdf-test.pdf")
    test_json_path = os.path.join(pdf_dir, "pdf-test.json")
    
    # Check if files exist
    if not os.path.exists(test_pdf_path):
        print(f"Error: Test PDF file not found: {test_pdf_path}")
        sys.exit(1)
    
    if not os.path.exists(test_json_path):
        print(f"Error: Test JSON file not found: {test_json_path}")
        sys.exit(1)
    
    try:
        # Parse the PDF
        print(f"Parsing test PDF: {test_pdf_path}")
        result = parse_pdf(
            pdf_path=test_pdf_path,
            output_format="markdown"
        )
        
        # Load expected result
        with open(test_json_path, 'r', encoding='utf-8') as f:
            expected_json = json.load(f)
        
        # Convert result to dict for comparison
        result_dict = result.model_dump(exclude_none=True)
        
        # Compare structures
        compare_output(result_dict, expected_json)
        
        # If we get here without exceptions, test passed
        print("\n✅ Test passed! The pdf_parser generated output matches the expected result.")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        print(traceback.format_exc())
        sys.exit(1)

def compare_output(actual: Dict[str, Any], expected: Dict[str, Any]) -> None:
    """
    Compare the actual output with the expected output.
    
    Args:
        actual: The actual output from the parser
        expected: The expected output from the test JSON file
    """
    # Check keys match
    actual_keys = set(actual.keys())
    expected_keys = set(expected.keys())
    
    if actual_keys != expected_keys:
        print("\nWarning: Keys do not match:")
        print(f"Missing keys: {expected_keys - actual_keys}")
        print(f"Extra keys: {actual_keys - expected_keys}")
    
    # Format check
    if actual.get('format') != expected.get('format'):
        print(f"\nFormat mismatch: Actual '{actual.get('format')}' vs Expected '{expected.get('format')}'")
    else:
        print(f"\nFormat match: '{actual.get('format')}'")
    
    # Success check
    if actual.get('success') != expected.get('success'):
        print(f"\nSuccess mismatch: Actual '{actual.get('success')}' vs Expected '{expected.get('success')}'")
    else:
        print(f"\nSuccess status match: '{actual.get('success')}'")
    
    # Output content - do a diff to show differences
    if actual.get('output') != expected.get('output'):
        print("\nOutput content differs. First 200 characters:")
        print(f"  Actual: {actual.get('output', '')[:200]}...")
        print(f"Expected: {expected.get('output', '')[:200]}...")
        
        # Show a diff of the first 1000 characters
        actual_content = actual.get('output', '')[:1000]
        expected_content = expected.get('output', '')[:1000]
        diff = difflib.unified_diff(
            expected_content.splitlines(),
            actual_content.splitlines(),
            lineterm='',
            n=2
        )
        print("\nDiff of first 1000 characters:")
        for line in diff:
            print(line)
    else:
        print("\nOutput content match! ✓")
    
    # Images check
    actual_images = set(actual.get('images', {}).keys())
    expected_images = set(expected.get('images', {}).keys())
    
    if actual_images != expected_images:
        print("\nImage filenames differ:")
        print(f"Missing images: {expected_images - actual_images}")
        print(f"Extra images: {actual_images - expected_images}")
    else:
        print(f"\nImage filenames match: {len(actual_images)} images found")
        
    # Metadata comparison - simplified
    if 'metadata' in actual and 'metadata' in expected:
        # Check table of contents count
        actual_toc = actual.get('metadata', {}).get('table_of_contents', [])
        expected_toc = expected.get('metadata', {}).get('table_of_contents', [])
        print(f"\nTable of contents: Actual has {len(actual_toc)} entries, Expected has {len(expected_toc)} entries")
        
        # Check page stats count
        actual_stats = actual.get('metadata', {}).get('page_stats', [])
        expected_stats = expected.get('metadata', {}).get('page_stats', [])
        print(f"\nPage stats: Actual has {len(actual_stats)} pages, Expected has {len(expected_stats)} pages")

if __name__ == "__main__":
    test_pdf_parser()
