# Funsense Project Design Document

## Overview

Funsense is a comprehensive email processing and analysis system designed to collect, analyze, and organize email content for weekly reporting purposes. The system leverages LLM (Large Language Model) capabilities for content analysis, translation, and categorization, with a focus on bilingual (English/Chinese) support.

## System Architecture

The project is structured as a modular application with several key components:

1. **Command Line Interface**: A Typer-based CLI that serves as the main entry point for all operations
2. **Gmail API Integration**: Services for authentication, email retrieval, and organization
3. **Email Analysis**: LLM-powered content analysis and categorization
4. **Weekly Report Generation**: Streamlit application for report creation and editing

### High-Level Component Diagram

```
                                 ┌─────────────────┐
                                 │                 │
                                 │  Typer CLI App  │
                                 │                 │
                                 └────────┬────────┘
                                          │
                 ┌───────────────────────┬┴───────────────────────┐
                 │                       │                        │
        ┌────────▼────────┐    ┌─────────▼────────┐     ┌─────────▼────────┐
        │                 │    │                  │     │                  │
        │  Gmail API      │    │  Email Analysis  │     │  Weekly Report   │
        │  Integration    │    │                  │     │  Generation      │
        │                 │    │                  │     │                  │
        └─────────────────┘    └──────────────────┘     └──────────────────┘
```

## Interface Design

### Command Line Interface

The system uses Typer to provide a clean, well-documented command line interface with the following main commands:

1. `dump_emails_by_date`: Dump emails within a date range to JSON files
2. `analyze_emails_by_date`: Analyze emails within a date range
3. `weekly_report`: Launch a Streamlit app for weekly report generation and editing

### Web Interface

The weekly report generation system provides a Streamlit-based web interface with the following features:

1. Sidebar with filters and controls for:
   - Platform selection (WeChat/Medium)
   - Content filtering
   - Date range filtering
   - Statistics display
   - Report generation actions

2. Main content area with:
   - Post editing capabilities
   - Bilingual content support
   - Image and link management
   - Platform-specific formatting

## Data Model

### Email Analysis Model

The core data model for email analysis is implemented as a Pydantic model with the following key fields:

```python
class EmailAnalysis(BaseModel):
    email_id: str
    post_labels: List[str]
    post_content_cn: str
    post_content_en: str
    link_lists: List[str]
    post_summary_cn: str
    post_summary_en: str
    post_datetime: Optional[datetime]
    source_language: Optional[str]
    confidence_score: Optional[float]
```

### Weekly Report Model

The weekly report system uses two main data models:

```python
class WeeklyPost(BaseModel):
    email_id: str
    post_datetime: str
    title_cn: str
    title_en: str
    post_content_cn: str
    post_content_en: str
    post_labels: list[str]
    link_lists: list[str]
    user_input_cn: str
    user_input_en: str
    main_image: str
    main_link: str
    wechat_selected: bool
    medium_selected: bool

class WeeklyReport(BaseModel):
    start_date: str
    end_date: str
    week_number: int
    summary: str
    posts: list[WeeklyPost]
```


For organizing and categorizing content, the system implements a hierarchical label structure:

```python
class LabelNode(BaseModel):
    name: str
    parent: Optional[str]
    children: List[str]
    email_ids: Set[str]


```

## Function Implementation

### Gmail API Integration

The Gmail API integration is implemented through several service classes:

1. **EmailDumper**: Handles email extraction and JSON file creation
   - `dump_emails_by_labels`: Dumps emails with specific labels
   - `dump_emails_by_date_range`: Dumps emails within a date range



3. **MessageService**: Handles Gmail message operations
   - `list_messages`: Lists messages matching a query

### Email Analysis

Email analysis is performed using LLM-powered functions:

1. **get_email_analysis**: Extracts structured analysis from email content
   - Determines source language
   - Generates bilingual content and summaries
   - Extracts links



3. **translate_from_cn_to_en/translate_from_en_to_cn**: Provides bidirectional translation



### Weekly Report Generation

The weekly report system is implemented as a Streamlit application with:

1. **run_app**: Main entry point for the Streamlit application
2. **load_analyzed_emails**: Loads email data within a date range
3. **convert_to_weekly_post**: Converts email data to weekly post format
4. **generate_markdown_report**: Creates platform-specific markdown reports

## Data Flow

### Email Processing Flow

1. **Email Dumping**:
   - Authenticate with Gmail API
   - Query emails by date range or labels
   - Extract email content and metadata
   - Save to JSON files in structured directories (YYYY/MM/DD)

2. **Email Analysis**:
   - Load email JSON files
   - Process content with LLM for bilingual analysis
   - Extract links and generate summaries
   - Save analyzed data to JSON files



4. **Weekly Report Generation**:
   - Load analyzed emails for the specified week
   - Convert to weekly post format
   - Present in Streamlit UI for editing
   - Generate platform-specific markdown reports

## Configuration

The project uses dotenv for configuration with the following key settings:

1. **Gmail API Configuration**: Authentication credentials and API settings
2. **LLM Configuration**: Model selection, API endpoints, and parameters
3. **Directory Structure**: Paths for email dumps, reports, and datasets

## Error Handling

The system implements comprehensive error handling with:

1. Exception catching and stack trace printing for debugging
2. Graceful degradation when services are unavailable
3. User-friendly error messages in both CLI and web interfaces

## Future Enhancements

Potential areas for future development include:

1. **Enhanced LLM Integration**: Support for more models and improved prompts
2. **Advanced Analytics**: Deeper analysis of email content and trends
3. **Automated Report Generation**: Fully automated weekly report creation
4. **Expanded Social Media Integration**: Support for more platforms beyond Twitter
5. **User Interface Improvements**: Enhanced Streamlit UI with more features

## Conclusion

The Funsense project provides a comprehensive solution for email processing, analysis, and reporting with a focus on bilingual support and LLM-powered content understanding. Its modular architecture allows for easy extension and maintenance, while the use of modern Python libraries and best practices ensures code quality and performance.
