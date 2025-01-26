# Gmail Email Tagger

This project provides functionality to automatically analyze and tag Gmail emails based on their content. It uses the Gmail API to retrieve emails, analyze their content, and add appropriate labels.

## Features

- Retrieve emails from Gmail account
- Analyze email content using customizable rules
- Automatically tag emails with relevant labels
- Support for custom tagging rules

## Setup

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable the Gmail API
   - Create OAuth 2.0 credentials
   - Download the credentials and save as `credentials.json` in the project root

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **First Run**
   - Run the main script:
     ```bash
     python main.py
     ```
   - On first run, it will open a browser window for OAuth authentication
   - Grant the required permissions
   - The authentication token will be saved for future use

## Project Structure

```
├── gmail_api/
│   ├── auth.py           # Authentication handling
│   ├── email_service.py  # Gmail API interactions
│   └── email_analyzer.py # Email content analysis
├── main.py              # Main entry point
├── requirements.txt     # Project dependencies
└── README.md           # This file
```

## Default Tags

The system comes with default tags for:
- Urgent messages
- Finance-related emails
- Meeting invitations
- Reports
- Follow-up items

## Customization

You can add custom rules by modifying the `rules` dictionary in `email_analyzer.py` or using the `add_custom_rule` method:

```python
analyzer = EmailAnalyzer()
analyzer.add_custom_rule('project', r'\b(project|milestone|deadline)\b')
python dump_emails.py --labels-file labels.txt --output-dir email_dumps --verbose
python gmail_api/email_analyzer.py email_dumps/ -o analyzed_emails.json --verbose
```

## Error Handling

The system includes comprehensive error handling for:
- Authentication failures
- API request issues
- Email processing errors

All errors are logged with appropriate messages for debugging.

## Security

- Uses OAuth 2.0 for secure authentication
- Stores credentials securely
- Requires minimal permissions (modify only for adding labels)
- No email content is stored locally

## Contributing

Feel free to submit issues and enhancement requests!



## usage:
 # not include the end
 - python main_cli.py dump-emails-by-date 2025-01-04 2025-01-12 --output-dir email_dumps --verbose
 - python main_cli.py analyze-emails-by-date 2025-01-04 2025-01-12 --input-dir email_dumps  --verbose
 - python main_cli.py weekly-report --start-date 2025-01-04 --end-date 2025-01-12 --input-dir email_dumps --verbose
 - /Users/tinge/work/tinge/agent/venv/funsense_env/bin/streamlit run weekly_report/report_app.py -- --start-date 2025-01-12 --end-date 2025-01-20 --input-dir email_dumps
