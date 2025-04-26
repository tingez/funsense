import re
import os
import json
import typer
import asyncio
import traceback
from typing import Optional
from pathlib import Path

from gmail_api.email_analyzer import process_directory, process_date_range, process_date_range_labels
from gmail_api.auth import get_gmail_service
from gmail_api.email_dumper import EmailDumper
from googleapiclient.discovery import build
from few_shot_dataset import build_label_hierarchy, FewShotDataset
import datetime

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
def generate_labels_by_date(
    start_date: str = typer.Argument(..., help="Start date in format YYYY-MM-DD"),
    end_date: str = typer.Argument(..., help="End date in format YYYY-MM-DD"),
    input_dir: str = typer.Option("email_dumps", help="Directory containing email JSON files"),
    examples_file: str = typer.Option("./few_shot_examples.json", help="Path to few-shot examples JSON file"),
    overwrite: bool = typer.Option(False, help="Whether to overwrite existing labels"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """
    Generate labels for emails within a specified date range using few-shot learning.
    Labels will be added to the analyzed email JSON files as 'post_labels' field.
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
            print(f"Generating labels for emails from {start_date} to {end_date}")
            print(f"Input directory: {input_dir}")
            print(f"Using examples from: {examples_file}")

        # Process emails
        result = asyncio.run(process_date_range_labels(
            input_dir=input_dir,
            start_date=start_date,
            end_date=end_date,
            examples_file=examples_file,
            overwrite=overwrite,
            verbose=verbose
        ))

        print(f"Successfully generated labels for {len(result)} emails")

    except Exception as e:
        print(f"Error generating labels: {str(e)}")
        print("Stack trace:")
        print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def generate_few_shot_dataset(
    dumps_dir: str = typer.Option("email_dumps", help="Directory containing email dump JSON files"),
    analyzed_file: str = typer.Option("analyzed_emails_deepseek.json", help="Analyzed emails JSON file"),
    output_file: str = typer.Option("label_hierarchy.json", help="Output file for label hierarchy"),
    examples_file: str = typer.Option("few_shot_examples.json", help="Output file for few-shot examples"),
    num_examples: int = typer.Option(5, help="Number of examples to include in the prompt"),
    min_examples_per_label: int = typer.Option(1, help="Minimum number of examples per label"),
    max_examples_per_label: int = typer.Option(None, help="Maximum number of examples per label. If None, will be calculated to ensure balanced representation")
):
    """
    Generate few-shot learning dataset from email dumps and analyzed content.
    The dataset will include hierarchical label structure and examples for training.
    Ensures balanced representation across labels with minimum examples per label.
    """
    try:
        # Build label hierarchy from email dumps
        print("Building label hierarchy from email dumps...")
        hierarchy = build_label_hierarchy(dumps_dir)
        
        # Save label hierarchy
        print(f"Saving label hierarchy to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(hierarchy.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Load analyzed emails
        print(f"Loading analyzed emails from {analyzed_file}...")
        with open(analyzed_file, 'r', encoding='utf-8') as f:
            analyzed_data = json.load(f)
        
        # Generate few-shot dataset
        print("Generating few-shot examples...")
        dataset = FewShotDataset(hierarchy, analyzed_data)
        dataset.generate_examples(
            min_examples_per_label=min_examples_per_label,
            max_examples_per_label=max_examples_per_label
        )
        
        # Save examples
        print(f"Saving few-shot examples to {examples_file}...")
        examples_data = [example.model_dump() for example in dataset.examples]
        with open(examples_file, 'w', encoding='utf-8') as f:
            json.dump(examples_data, f, indent=2, ensure_ascii=False)
        
        # Generate and print sample prompt
        print("\nSample few-shot prompt:")
        print(dataset.generate_prompt(num_examples))
        
        print(f"\nTotal examples generated: {len(dataset.examples)}")
        print("Done!")
        
    except Exception as e:
        traceback.print_exc()
        print(f"Error generating few-shot dataset: {str(e)}")
        raise

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

if __name__ == "__main__":
    app()