import re
import os
import json
import typer
import asyncio
import traceback
from typing import Optional
from pathlib import Path

from gmail_api.email_analyzer import process_directory, process_date_range
from gmail_api.auth import get_gmail_service
from gmail_api.email_dumper import EmailDumper
from googleapiclient.discovery import build
import datetime

# Import the PDF parser
from tools.pdf.pdf_parser import parse_pdf

app = typer.Typer(pretty_exceptions_show_locals=False)

@app.command()
def trim_data_according_to_openai():
    email_map = {}
    input_dir = Path("email_dumps")
    json_files = list(input_dir.glob("*.json"))
    if not json_files:
        print("No JSON files found")
        return None

    # calculate how many email_data in different json files will be processed
    total_emails = 0
    all_emails = []
    for file_path in json_files:
        try:
            #print(f"Processing {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                email_datas = json.load(f)
            # Handle both single email and list of emails
            if not isinstance(email_datas, list):
                email_datas = [email_datas]

            for email_data in email_datas:
                email_map[email_data['id']] = email_data
        except Exception as e:
            traceback.print_exc()
            print(f"Error processing {file_path.name}: {e}")
            continue
    print(f"Total emails to process: {len(email_map)}")

    qwen_data = {}
    with open('./analyzed_emails_qwen.json', 'r', encoding='utf-8') as f:
        qwen_data = json.load(f)
    print(f"Total emails to process: {len(qwen_data)}")

    openai_data = {}
    with open('./analyzed_emails_openai.json', 'r', encoding='utf-8') as f:
        openai_data = json.load(f)
    print(f"Total emails to process: {len(openai_data)}")

    deepseek_data = {}
    with open('./analyzed_emails_deepseek.json', 'r', encoding='utf-8') as f:
        deepseek_data = json.load(f)
    print(f"Total emails to process: {len(deepseek_data)}")

    llama_data = {}
    with open('./analyzed_emails_llama.json', 'r', encoding='utf-8') as f:
        llama_data = json.load(f)
    print(f"Total emails to process: {len(llama_data)}")

    output_openai_data = {}
    output_qwen_data = {}
    output_deepseek_data = {}
    output_llama_data = {}
    output_email_data = {}


    for email_id, email_data in openai_data.items():
        if email_id in email_map:
            output_email_data[email_id] = email_map[email_id]
            output_openai_data[email_id] = openai_data[email_id]
            output_qwen_data[email_id] = qwen_data[email_id]
            output_deepseek_data[email_id] = deepseek_data[email_id]
            output_llama_data[email_id] = llama_data[email_id]

            del output_email_data[email_id]['thread_id']
            del output_email_data[email_id]['headers']['message-id']
            del output_email_data[email_id]['headers']['from']
            del output_email_data[email_id]['headers']['to']
            del output_email_data[email_id]['headers']['content-type']


    with open('./data/analyzed_emails_openai.json', 'w', encoding='utf-8') as f:
        json.dump(output_openai_data, f, ensure_ascii=False, indent=2)
    with open('./data/analyzed_emails_qwen.json', 'w', encoding='utf-8') as f:
        json.dump(output_qwen_data, f, ensure_ascii=False, indent=2)
    with open('./data/analyzed_emails_deepseek.json', 'w', encoding='utf-8') as f:
        json.dump(output_deepseek_data, f, ensure_ascii=False, indent=2)
    with open('./data/analyzed_emails_llama.json', 'w', encoding='utf-8') as f:
        json.dump(output_llama_data, f, ensure_ascii=False, indent=2)
    with open('./data/raw_emails.json', 'w', encoding='utf-8') as f:
        json.dump(output_email_data, f, ensure_ascii=False, indent=2)



@app.command()
def analyze(
    input_dir: Path = typer.Argument(
        ...,
        help="Directory containing email JSON files",
        exists=True,
        dir_okay=True,
        file_okay=False
    ),
    output_file: Path = typer.Option(
        "analyzed_emails.json",
        "--output", "-o",
        help="Output JSON file for analyzed emails"
    )
):
    """Analyze email content from JSON dumps using LLM."""
    try:
        # Process emails
        results = asyncio.run(process_directory(input_dir, output_file))

        if not results:
            print("No emails were successfully processed")
            raise typer.Exit(1)

        # Save results
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # Print summary
        print(f"\nSuccessfully processed {len(results)} emails")
        print(f"Results saved to: {output_file}")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        raise typer.Exit(1)


def __parse_label_line(line: str) -> str:
    """Extract the actual label name from a line that might include ID and prefix."""
    # Remove the leading "- " if present
    line = line.lstrip('- ')

    # Extract the label name (everything before " (ID: Label_...")
    match = re.match(r'^([^(]+?)(?:\s+\(ID: Label_\d+\))?$', line.strip())
    if match:
        return match.group(1).strip()
    return line.strip()

@app.command()
def dump_emails(
    labels_file: str = typer.Option(..., help="File containing label names, one per line"),
    output_dir: str = typer.Option("email_dumps", help="Directory to save email dumps"),
    skip_empty: bool = typer.Option(True, help="Skip labels with no emails"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """
    Dump emails with specified labels to JSON files.
    """
    try:
        # Set verbose flag
        if verbose:
            print("Verbose mode enabled")

        # Read and parse labels from file
        print("Reading labels file...")
        with open(labels_file, 'r') as f:
            labels = [__parse_label_line(line) for line in f if line.strip()]
            labels = [label for label in labels if label]  # Remove any empty results

        if not labels:
            print("No labels found in the input file")
            raise typer.Exit(1)

        print(f"\nFound {len(labels)} labels to process:")
        for label in labels:
            print(f"  • {label}")

        # Get Gmail service
        print("Authenticating with Gmail...")
        credentials = get_gmail_service()
        if not credentials:
            print("Failed to get Gmail credentials")
            raise typer.Exit(1)

        service = build('gmail', 'v1', credentials=credentials)
        dumper = EmailDumper(service)

        # Create output directory
        print("Creating output directory...")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Dump emails
        print("Starting email dump...")
        output_file = dumper.dump_emails_by_labels(labels, output_dir)

        if output_file:
            print("\nEmail dump completed successfully! ")
            print(f"Output file: {output_file}")
        else:
            print("\nFailed to dump emails ")
            raise typer.Exit(1)

    except Exception as e:
        print(f"Error: {str(e)}")
        raise typer.Exit(1)


"""
python main_cli.py dump-emails-by-date 2024-01-01 2024-01-31 --output-dir email_dumps --verbose
"""
@app.command()
def dump_emails_by_date(
    start_date: str = typer.Argument(..., help="Start date in format YYYY-MM-DD"),
    end_date: str = typer.Argument(..., help="End date in format YYYY-MM-DD"),
    output_dir: str = typer.Option("email_dumps", help="Directory to save email dumps"),
    overwrite: bool = typer.Option(False, help="Whether to overwrite existing files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """
    Dump all emails within a specified date range to JSON files.
    Files will be organized in directories: output_dir/YYYY/MM/DD/email_id.json
    """
    try:
        # Validate date format
        try:
            datetime.datetime.strptime(start_date, "%Y-%m-%d")
            datetime.datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            print(f"Invalid date format. Please use YYYY-MM-DD format. Error: {e}")
            return

        if verbose:
            print(f"Authenticating with Gmail API...")

        creds = get_gmail_service()
        if not creds:
            print("Failed to authenticate with Gmail API")
            return

        service = build('gmail', 'v1', credentials=creds)
        dumper = EmailDumper(service)

        if verbose:
            print(f"Dumping emails from {start_date} to {end_date}")
            print(f"Output directory: {output_dir}")

        created_files = dumper.dump_emails_by_date_range(
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            overwrite=overwrite,
            verbose=verbose
        )

        if verbose:
            print(f"Successfully dumped {len(created_files)} emails")

    except Exception as e:
        print(f"Error: {str(e)}")
        print("Stack trace:")
        print(traceback.format_exc())


@app.command()
def analyze_emails_by_date(
    start_date: str = typer.Argument(..., help="Start date in format YYYY-MM-DD"),
    end_date: str = typer.Argument(..., help="End date in format YYYY-MM-DD"),
    input_dir: str = typer.Option("email_dumps", help="Directory containing email JSON files"),
    output_dir: Optional[str] = typer.Option(None, help="Directory to save analyzed emails (defaults to input_dir)"),
    overwrite: bool = typer.Option(False, help="Whether to overwrite existing analysis files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """
    Analyze emails within a specified date range.
    Files will be analyzed and saved as: output_dir/YYYY/MM/DD/email_id_analyzed.json
    """
    try:
        # Validate date format
        try:
            datetime.datetime.strptime(start_date, "%Y-%m-%d")
            datetime.datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            print(f"Invalid date format: {e}")
            print("Please use YYYY-MM-DD format")
            raise typer.Exit(1)

        if verbose:
            print(f"Analyzing emails from {start_date} to {end_date}")
            print(f"Input directory: {input_dir}")
            print(f"Output directory: {output_dir or input_dir}")

        # Process emails
        result = asyncio.run(process_date_range(
            input_dir=input_dir,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            overwrite=overwrite,
            verbose=verbose
        ))

        print(f"Successfully analyzed {len(result)} emails")

    except Exception as e:
        print(f"Error analyzing emails: {str(e)}")
        print("Stack trace:")
        print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def weekly_report(
    start_date: str = typer.Argument(..., help="Start date in format YYYY-MM-DD"),
    end_date: str = typer.Argument(..., help="End date in format YYYY-MM-DD"),
    input_dir: str = typer.Option("email_dumps", help="Directory containing email JSON files"),
    overwrite: bool = typer.Option(False, help="Whether to overwrite existing JSON files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """
    Start a Streamlit app to generate and edit weekly reports for emails within a date range.
    """
    try:
        if verbose:
            print(f"Starting weekly report app for date range {start_date} to {end_date}")
            print(f"Input directory: {input_dir}")

        import sys
        import streamlit.web.cli as stcli

        # Create a new sys.argv for Streamlit
        sys.argv = [
            "/Users/tinge/work/tinge/agent/venv/funsense_env/bin/streamlit",
            "run",
            os.path.join(os.path.dirname(__file__), "weekly_report", "report_app.py"),
            "--",
            input_dir,
            start_date,
            end_date,
            str(overwrite)
        ]

        sys.exit(stcli.main())
    except Exception as e:
        print(traceback.format_exc())
        raise typer.Exit(1)

@app.command()
def dump(
    start_date: str = typer.Option(..., help="Start date in YYYY-MM-DD format"),
    end_date: str = typer.Option(..., help="End date in YYYY-MM-DD format"),
    output_dir: str = typer.Option(..., help="Directory to save email dumps"),
    overwrite: bool = typer.Option(False, help="Whether to overwrite existing files"),
    verbose: bool = typer.Option(False, help="Enable verbose logging")
):
    """Dump emails from Gmail API."""
    try:
        from gmail_api.email_dumper import dump_emails
        dump_emails(start_date, end_date, output_dir, overwrite, verbose)
    except Exception as e:
        print(f"Error dumping emails: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise typer.Exit(1)

@app.command()
def analyze(
    start_date: str = typer.Option(..., help="Start date in YYYY-MM-DD format"),
    end_date: str = typer.Option(..., help="End date in YYYY-MM-DD format"),
    input_dir: str = typer.Option(..., help="Directory containing email dumps"),
    overwrite: bool = typer.Option(False, help="Whether to overwrite existing files"),
    verbose: bool = typer.Option(False, help="Enable verbose logging")
):
    """Analyze dumped emails."""
    try:
        from gmail_api.email_analyzer import analyze_emails
        analyze_emails(start_date, end_date, input_dir, overwrite, verbose)
    except Exception as e:
        print(f"Error analyzing emails: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise typer.Exit(1)

@app.command()
def weekly_report(
    start_date: str = typer.Option(..., help="Start date in YYYY-MM-DD format"),
    end_date: str = typer.Option(..., help="End date in YYYY-MM-DD format"),
    input_dir: str = typer.Option(..., help="Directory containing email dumps"),
    overwrite: bool = typer.Option(False, help="Whether to overwrite existing files"),
    verbose: bool = typer.Option(False, help="Enable verbose logging")
):
    """Start a Streamlit app to edit weekly report."""
    try:
        from weekly_report.report_app import run_app
        print(f"Starting weekly report app for date range {start_date} to {end_date}")
        print(f"Input directory: {input_dir}")
        run_app(input_dir, start_date, end_date, overwrite)
    except Exception as e:
        print(f"Error running weekly report app: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise typer.Exit(1)

@app.command()
def convert_pdf(
    pdf_path: str = typer.Argument(..., help="Path to the PDF file"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Path to save the markdown output"),
    page_range: Optional[str] = typer.Option(None, "--pages", "-p", help="Page range to convert (e.g., '0,5-10,20')"),
    languages: Optional[str] = typer.Option(None, "--langs", "-l", help="Comma separated list of languages for OCR"),
    force_ocr: bool = typer.Option(False, "--force-ocr", help="Force OCR on all pages"),
    paginate: bool = typer.Option(False, "--paginate", help="Whether to paginate the output"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown, json, or html)"),
    api_url: str = typer.Option("http://192.168.8.104:8001", "--api-url", help="The base URL of the Marker API")
):
    """Convert a PDF file to markdown using the Marker API."""
    try:
        print(f"Converting PDF: {pdf_path}")
        result = parse_pdf(
            pdf_path=pdf_path,
            page_range=page_range,
            languages=languages,
            force_ocr=force_ocr,
            paginate_output=paginate,
            output_format=format,
            api_url=api_url
        )

        if not result.success:
            print("Error: Conversion failed")
            raise typer.Exit(1)

        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result.output)
                print(f"Markdown content saved to: {output_file}")
            except Exception as e:
                print(f"Error saving output file: {e}")
                print(traceback.format_exc())
                raise typer.Exit(1)
        else:
            print("\nMarkdown Content:")
            print("="*50)
            print(result.output)
    except Exception as e:
        print(f"Error converting PDF: {e}")
        print(traceback.format_exc())
        raise typer.Exit(1)


if __name__ == "__main__":
    app()