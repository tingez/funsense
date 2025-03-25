import os
import asyncio
import json
from tqdm import tqdm
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from promptic import llm
import re
from datamodel.email import EmailAnalysis

SYSTEM_PROMPT = """You are an AI assistant that analyzes email content and provides structured analysis.
In order to keep bilingual support, you need to analyze the email in both Chinese and English.
If the emall is in Chinese, you need translate it to English. If the email is in English, you need translate it to Chinese.
Your task is to analyze the email and provide:
1. source_language: The original language of the email content (e.g., 'en' for English, 'cn' for Chinese)
2. if source_language is Chinese('cn'), post_content_cn will be orignal content removed any links, post_summary_cn will be a concise summary for post_content_cn, post_content_en will be translate post_content_cn to English, post_summary_en will be a concise summary for post_content_en.
3. if source_language is English('en'), post_content_en will be orignal content removed any links, post_summary_en will be a concise summary for post_content_en, post_content_cn will be translate post_content_en to Chinese, post_summary_cn will be a concise summary for post_content_cn.
4. link_lists: Extract any URLs or links from the original email content
5. post_datetime: The timestamp when the email was sent or received

Return the analysis in JSON format.
"""

LABEL_SYSTEM_PROMPT = """You are an AI assistant that generates labels for content.
Given examples of content and their corresponding labels, your task is to generate appropriate labels for new content.
The labels should be consistent with the examples provided and reflect the main topics or categories of the content.

Rules:
1. Return ONLY a JSON array of label strings, nothing else
2. Keep labels concise and lowercase
3. Use existing labels from examples when possible
4. Add new labels only when necessary
5. Focus on the main topics and technologies mentioned

Example output format: ["label1", "label2", "label3"]
"""


TRANSLATE_FROM_EN_TO_CN_SYSTEM_PROMPT = """You are an AI assistant that translates content from English to Chinese.

Rules:
1. Keep the same format of the original content
2. Return ONLY the translated content, nothing else
"""

TRANSLATE_FROM_CN_TO_EN_SYSTEM_PROMPT = """You are an AI assistant that translates content from Chinese to English.

Rules:
1. Keep the same format of the original content
2. Return ONLY the translated content, nothing else
"""

@llm(
    #model='ollama/llama3.1:8b-instruct-fp16', 
    #model='ollama/qwen2.5:7b-instruct-fp16',
    model='deepseek/deepseek-chat',
    #api_base='http://192.168.8.119:11434',
    temperature=0,
    top_p=0.1,
    timeout=30,
    debug=False,
    system=SYSTEM_PROMPT
)
def get_email_analysis(content: str) -> EmailAnalysis:
    """Extract structured analysis from email content {content}"""

@llm(
    model='ollama/qwen2.5:7b-instruct-fp16',
    #model='deepseek/deepseek-chat',
    api_base='http://192.168.8.120:11434',
    temperature=0,
    top_p=0.1,
    timeout=30,
    debug=True,
    system=LABEL_SYSTEM_PROMPT
)
def generate_labels(content: str, examples: str) -> List[str]:
    """Generate labels for the following content based on examples.
    
    Here are some examples:
    {examples}
    
    Now generate labels for this content:
    {content}
    
    Return ONLY a JSON array of label strings, nothing else.
    For example: ["label1", "label2", "label3"]
    """

@llm(
    model='ollama/qwen2.5:7b-instruct-fp16',
    api_base='http://192.168.8.120:11434',
    temperature=0,
    top_p=0.1,
    timeout=30,
    debug=True,
    system=TRANSLATE_FROM_EN_TO_CN_SYSTEM_PROMPT
)
def translate_from_en_to_cn(content: str) -> str:
    """Translate the following content from English to Chinese.

    {content}

    Return ONLY the translated content, nothing else.
    """

@llm(
    model='ollama/qwen2.5:7b-instruct-fp16',
    api_base='http://192.168.8.120:11434',
    temperature=0,
    top_p=0.1,
    timeout=30,
    debug=True,
    system=TRANSLATE_FROM_CN_TO_EN_SYSTEM_PROMPT
)
def translate_from_cn_to_en(content: str) -> str:
    """Translate the following content from Chinese to English

    {content}

    Return ONLY the translated content, nothing else.
    """


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text using regex"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return list(set(re.findall(url_pattern, text)))

async def analyze_email(email_data: Dict[str, Any]) -> Optional[EmailAnalysis]:
    """Analyze single email content"""
    try:
        # Format content for analysis
        content = f"""
        Subject: {email_data.get('headers', {}).get('subject', 'no subject')}
        Post_id: {email_data.get('id', '')} 
        Date: {email_data.get('headers', {}).get('date', '')}
        Label: {email_data.get('label_name', '')}

        
        Content:
        {email_data.get('plain_text', '')}
        """

        # Get LLM analysis
        analysis = get_email_analysis(content)
        print(analysis.model_dump_json())
        return analysis
        
    except Exception as e:
        # print stack trace
        traceback.print_exc()
        print(f"Analysis error: {e}")
        return None

async def process_directory(input_dir: Path, output_file: Path) -> Dict[str, Dict]:
    """Process all emails in directory"""

    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            result_map = json.load(f)
    else:
        result_map = {}

    for key, value in result_map.items():
        result_map[key] = EmailAnalysis.model_validate(value).model_dump() if isinstance(value, dict) else value

    json_files = list(input_dir.glob("*.json"))
    
    if not json_files:
        print("No JSON files found")
        return result_map

    # calculate how many email_data in different json files will be processed
    total_emails = 0
    all_emails = []
    for file_path in json_files:
        try:
            print(f"Processing {file_path.name}")
            with open(file_path, 'r', encoding='utf-8') as f:
                email_datas = json.load(f)
            # Handle both single email and list of emails
            if not isinstance(email_datas, list):
                email_datas = [email_datas]
            total_emails += len(email_datas)
            all_emails.extend(email_datas)
        except Exception as e:
            traceback.print_exc()
            print(f"Error processing {file_path.name}: {e}")
            continue
    print(f"Total emails to process: {total_emails}")

    for email_data in tqdm(all_emails):
        try:
            email_id = email_data.get('id', '')
            # Check if email has already been processed
            if email_id in result_map:
                email_label = email_data.get('label_name', '')
                if email_label not in result_map[email_id]['post_labels']:
                    result_map[email_id]['post_labels'].append(email_label)
                continue
            if analysis := await analyze_email(email_data):
                result_map[email_id] = analysis.model_dump()
            # Save results
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_map, f, ensure_ascii=False, indent=2)

        except Exception as e:
            traceback.print_exc()
            print(f"Error processing {file_path.name}: {e}")
            continue
            
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_map, f, ensure_ascii=False, indent=2)
        
    return result_map

async def process_date_range(
    input_dir: str,
    start_date: str,
    end_date: str,
    output_dir: Optional[str] = None,
    overwrite: bool = False,
    verbose: bool = False
) -> Dict[str, Dict]:
    """
    Process emails within a specified date range.
    
    Args:
        input_dir: Base directory containing email JSON files
        start_date: Start date in format YYYY-MM-DD
        end_date: End date in format YYYY-MM-DD
        output_dir: Directory to save analyzed emails (defaults to input_dir)
        overwrite: Whether to overwrite existing analysis files
        verbose: Whether to enable verbose logging
    """
    try:
        # Convert dates to datetime objects for comparison
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        if verbose:
            print(f"Processing emails from {start_date} to {end_date}")
            print(f"Input directory: {input_dir}")
            print(f"Output directory: {output_dir or input_dir}")

        # Initialize result map
        result_map = {}
        
        # Walk through the directory structure
        for year in range(start_dt.year, end_dt.year + 1):
            year_dir = os.path.join(input_dir, str(year))
            if not os.path.exists(year_dir):
                continue
                
            for month in range(1, 13):
                if year == start_dt.year and month < start_dt.month:
                    continue
                if year == end_dt.year and month > end_dt.month:
                    continue
                    
                month_dir = os.path.join(year_dir, str(month).zfill(2))
                if not os.path.exists(month_dir):
                    continue
                    
                for day in range(1, 32):
                    try:
                        current_dt = datetime(year, month, day)
                    except ValueError as e:
                        print(f"Invalid date: {year}-{month}-{day}")
                        continue

                    if current_dt < start_dt or current_dt > end_dt:
                        continue
                        
                    day_dir = os.path.join(month_dir, str(day).zfill(2))
                    if not os.path.exists(day_dir):
                        continue
                        
                    if verbose:
                        print(f"Processing directory: {day_dir}")
                        
                    # Process all JSON files in the day directory
                    for file_name in os.listdir(day_dir):
                        if not file_name.endswith('.json') or file_name.endswith('_analyzed.json'):
                            continue
                            
                        input_file = os.path.join(day_dir, file_name)
                        email_id = os.path.splitext(file_name)[0]
                        
                        # Determine output path
                        if output_dir:
                            out_day_dir = os.path.join(output_dir, str(year), str(month).zfill(2), str(day).zfill(2))
                            os.makedirs(out_day_dir, exist_ok=True)
                            output_file = os.path.join(out_day_dir, f"{email_id}_analyzed.json")
                        else:
                            output_file = os.path.join(day_dir, f"{email_id}_analyzed.json")
                            
                        # Skip if analysis exists and not overwriting
                        if os.path.exists(output_file) and not overwrite:
                            if verbose:
                                print(f"Skipping existing analysis: {output_file}")
                            continue
                            
                        try:
                            # Load and analyze email
                            with open(input_file, 'r', encoding='utf-8') as f:
                                email_data = json.load(f)
                                
                            if verbose:
                                print(f"Analyzing email: {email_id}")
                                
                            if analysis := await analyze_email(email_data):
                                result_map[email_id] = analysis.model_dump()
                                
                                # Save individual analysis
                                with open(output_file, 'w', encoding='utf-8') as f:
                                    json.dump(analysis.model_dump(), f, ensure_ascii=False, indent=2)
                                    
                        except Exception as e:
                            print(f"Error processing {input_file}: {str(e)}")
                            if verbose:
                                traceback.print_exc()
                            continue
        
        if verbose:
            print(f"Successfully analyzed {len(result_map)} emails")
        return result_map
        
    except Exception as e:
        print(f"Error processing date range: {str(e)}")
        print("Stack trace:")
        print(traceback.format_exc())
        return {}

async def process_date_range_labels(
    input_dir: str,
    start_date: str,
    end_date: str,
    examples_file: str = "./few_shot_examples.json",
    overwrite: bool = False,
    verbose: bool = False
) -> Dict[str, List[str]]:
    """
    Process emails within a date range to generate labels using few-shot learning.
    
    Args:
        input_dir: Base directory containing analyzed email JSON files
        start_date: Start date in format YYYY-MM-DD
        end_date: End date in format YYYY-MM-DD
        examples_file: Path to few-shot examples JSON file
        overwrite: Whether to overwrite existing labels
        verbose: Whether to enable verbose logging
    """
    try:
        # Load few-shot examples
        with open(examples_file, 'r', encoding='utf-8') as f:
            examples_data = json.load(f)
            
        # Format examples for the prompt
        examples_text = "\n".join([
            f"Content: {example['content']}\nExpected labels: {json.dumps(example['labels'])}"
            for example in examples_data[:]  # Use only first 5 examples to keep prompt size reasonable
        ])
        
        if verbose:
            print(f"Loaded {len(examples_data)} few-shot examples")
            
        # Convert dates to datetime objects
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        result_map = {}
        
        # Walk through directory structure
        for year in range(start_dt.year, end_dt.year + 1):
            year_dir = os.path.join(input_dir, str(year))
            if not os.path.exists(year_dir):
                continue
                
            for month in range(1, 13):
                if year == start_dt.year and month < start_dt.month:
                    continue
                if year == end_dt.year and month > end_dt.month:
                    continue
                    
                month_dir = os.path.join(year_dir, str(month).zfill(2))
                if not os.path.exists(month_dir):
                    continue
                    
                for day in range(1, 32):
                    try:
                        current_dt = datetime(year, month, day)
                    except Exception as e:
                        print(f"Invalid date: {year}-{month}-{day}")
                        continue
                    if current_dt < start_dt or current_dt > end_dt:
                        continue
                        
                    day_dir = os.path.join(month_dir, str(day).zfill(2))
                    if not os.path.exists(day_dir):
                        continue
                        
                    if verbose:
                        print(f"Processing directory: {day_dir}")
                        
                    # Process analyzed JSON files
                    for file_name in os.listdir(day_dir):
                        if not file_name.endswith('_analyzed.json'):
                            continue
                            
                        file_path = os.path.join(day_dir, file_name)
                        email_id = file_name.replace('_analyzed.json', '')
                        
                        try:
                            # Load analyzed email
                            with open(file_path, 'r', encoding='utf-8') as f:
                                email_data = json.load(f)
                                
                            # Skip if already has labels and not overwriting
                            if not overwrite and email_data.get('post_labels'):
                                if verbose:
                                    print(f"Skipping {email_id}: already has labels")
                                continue
                                
                            if verbose:
                                print(f"Generating labels for {email_id}")
                                
                            # Generate labels using few-shot learning
                            content = email_data.get('post_content_en', '')
                            if not content:
                                print(f"Warning: No English content found for {email_id}")
                                continue
                                
                            labels = generate_labels(content, examples_text)
                            email_data['post_labels'] = labels
                            result_map[email_id] = labels
                            
                            # Save updated email data
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(email_data, f, ensure_ascii=False, indent=2)
                                
                        except Exception as e:
                            print(f"Error processing {file_path}: {str(e)}")
                            if verbose:
                                traceback.print_exc()
                            continue
                            
        if verbose:
            print(f"Successfully generated labels for {len(result_map)} emails")
        return result_map
        
    except Exception as e:
        print(f"Error processing date range: {str(e)}")
        print("Stack trace:")
        print(traceback.format_exc())
        return {}