# Weekly Report Application Design Document

## Overview
The Weekly Report Application is a Streamlit-based web application for managing and generating bilingual (Chinese-English) weekly reports from email content. The application supports content translation, filtering, and report generation in multiple formats (WeChat, Medium, and Notion).

## Technical Stack Requirements

### Core Technologies
- **Python Environment**: Virtual environment at `/Users/tinge/work/tinge/agent/venv/funsense_env/bin/python`
- **CLI Framework**: Typer with `pretty_exceptions_show_locals=False`
- **Configuration**: dotenv with `load_dotenv(override=True)`
- **Web Framework**: Streamlit for UI
- **Data Validation**: Pydantic V2
- **Date Handling**: Delorean for datetime transformations
- **Excel Processing**: openpyxl for spreadsheet operations
- **Browser Automation**: Playwright (not Selenium)

### Development Guidelines
1. Use print statements for:
   - Debugging
   - Error handling
   - User messages
2. Avoid:
   - logging module
   - rich for user messages
   - pathlib for file paths
   - console for printing
3. Always print stack traces for error handling

## Data Models

### WeeklyPost
- **Purpose**: Represents a single post in the weekly report with bilingual content
- **Implementation**: Pydantic BaseModel
- **Fields**:
  - `email_id`: Unique identifier (str)
  - `post_datetime`: Timestamp (str)
  - `title_cn/en`: Bilingual titles (str)
  - `post_content_cn/en`: Bilingual content (str)
  - `post_labels`: List of labels (list[str])
  - `link_lists`: URLs (list[str])
  - `user_input_cn/en`: User input (str)
  - `main_image`: Image URL (str)
  - `main_link`: Primary URL (str)
  - `wechat_selected`: WeChat flag (bool)
  - `medium_selected`: Medium flag (bool)
- **Validators**:
  - field_validator for boolean fields (handles string 'true'/'false' conversion)

### WeeklyReport
- **Purpose**: Container for weekly report data with metadata
- **Implementation**: Pydantic BaseModel
- **Fields**:
  - `start_date`: Period start (str)
  - `end_date`: Period end (str)
  - `week_number`: ISO week (int)
  - `summary`: Report text (str)
  - `posts`: WeeklyPost list (list[WeeklyPost])

## Core Functions

### Email Processing
1. `load_analyzed_emails`
   - **Purpose**: Load analyzed email data from JSON files within date range
   - **Input**: Directory path, start date, end date
   - **Process**: Recursively scan directories by year/month/day, load JSON files
   - **Output**: List of email data dictionaries

2. `convert_to_weekly_post`
   - **Purpose**: Convert email data dictionary to WeeklyPost objects
   - **Input**: Email data dictionary
   - **Process**: Map fields, handle label parsing, set default values
   - **Output**: WeeklyPost object

3. `get_week_number`
   - **Purpose**: Extract ISO week number from date string
   - **Input**: Date string (YYYY-MM-DD format)
   - **Process**: Parse date string and extract week number
   - **Output**: Integer week number

### Report Generation
1. `generate_markdown_report`
   - **Purpose**: Generate platform-specific reports (WeChat or Medium)
   - **Input**: WeeklyReport, is_wechat flag
   - **Process**: Filter posts, group by labels, format content based on platform
   - **Output**: Markdown formatted string

2. `generate_notion_report`
   - **Purpose**: Generate Notion-specific format (English content with WeChat layout)
   - **Input**: WeeklyReport
   - **Process**: Filter WeChat posts, format with English content
   - **Output**: Markdown formatted string

3. `_group_posts_by_labels`
   - **Purpose**: Helper function to group posts by their labels
   - **Input**: List of WeeklyPost objects
   - **Process**: Create dictionary with labels as keys, posts as values
   - **Output**: Dictionary mapping label strings to post lists

4. `_format_labels_markdown`
   - **Purpose**: Format labels as bold markdown text
   - **Input**: Comma-separated labels string
   - **Process**: Split, clean, and format labels with markdown
   - **Output**: Formatted markdown string for labels

### Session State Management

1. `_init_session_state`
   - **Purpose**: Initialize Streamlit session state variables
   - **Process**: Set up report, wechat_count, medium_count

2. `_load_existing_report`
   - **Purpose**: Load report from existing JSON file
   - **Input**: Target file path
   - **Process**: Read JSON, parse into WeeklyReport, update counts
   - **Output**: (WeeklyReport, success/error message)

3. `_create_new_report`
   - **Purpose**: Create new report from analyzed emails
   - **Input**: Input directory, date range, week number
   - **Process**: Load emails, convert to WeeklyPost objects, create report
   - **Output**: (WeeklyReport, success message)

4. `_get_report_file_path`
   - **Purpose**: Calculate target file path and week number
   - **Input**: Input directory, end date
   - **Process**: Extract year, create weekly directory, build file path
   - **Output**: (target file path, week number)

### UI Components

#### Sidebar Components

1. `_render_sidebar_header`
   - **Purpose**: Display report metadata
   - **Process**: Show date range, week number, input directory

2. `_render_sidebar_summary`
   - **Purpose**: Allow editing of weekly summary
   - **Process**: Provide text area for markdown summary

3. `_render_sidebar_filters`
   - **Purpose**: Provide filtering controls
   - **Process**: Platform filters (WeChat, Medium, Future)
               Content filters (Image, Link, CN, EN)
               Date range filters (All Time, Last 24h, Last Week)
   - **Output**: (platform_filter, content_filter, date_range_filter)

4. `_render_sidebar_stats`
   - **Purpose**: Display statistics about posts
   - **Input**: Report, filtered posts
   - **Process**: Show total/filtered counts, platform counts, content type metrics

5. `_render_sidebar_actions`
   - **Purpose**: Provide action buttons
   - **Input**: Report, target file, week number, input directory
   - **Process**: Save report button, download images button, generate reports buttons

#### Post Filtering

1. `_apply_platform_filter`
   - **Purpose**: Filter posts by platform (WeChat, Medium, Future)
   - **Input**: Post list, platform filter list
   - **Process**: Check each post against platform criteria
   - **Output**: Filtered post list

2. `_apply_content_filter`
   - **Purpose**: Filter posts by content (Image, Link, CN, EN)
   - **Input**: Post list, content filter list
   - **Process**: Check each post against content criteria
   - **Output**: Filtered post list

3. `_apply_date_filter`
   - **Purpose**: Filter posts by date range
   - **Input**: Post list, date range filter
   - **Process**: Check post dates against selected time window
   - **Output**: Filtered post list

#### Main Content Area

1. `_render_post_header`
   - **Purpose**: Display post header with platform selection checkboxes
   - **Input**: Post object, index, session state key
   - **Process**: Show title, checkboxes, update stats on change, track changes

2. `_render_post_content`
   - **Purpose**: Display and edit post content with translation features
   - **Input**: Post object, index, session state key
   - **Process**: Bilingual content editors, translation buttons, media sections

### Helper Functions

1. `download_image`
   - **Purpose**: Download an image from URL to local path
   - **Input**: URL, save path
   - **Process**: Request image, save to file, handle errors
   - **Output**: Success boolean

2. `_download_post_images`
   - **Purpose**: Batch download images for posts
   - **Input**: Post list, input directory
   - **Process**: Extract date, create directories, download images with progress bar

3. `_generate_platform_report`
   - **Purpose**: Generate and save report for specific platform
   - **Input**: Report, target file, week number, platform
   - **Process**: Generate proper format, save to file, provide feedback

## Application Flow

1. **Initialization Phase**
   - Parse command line arguments (argparse)
   - Configure Streamlit page layout
   - Initialize session state variables
   - Determine report file path

2. **Report Loading Phase**
   - Try to load existing report from file
   - Create new report if loading fails or doesn't exist
   - Update session state with loaded/created report

3. **UI Rendering Phase**
   - Render sidebar components (header, summary, filters, stats, actions)
   - Apply selected filters to posts
   - Render main content area with filtered posts
   - Provide refresh button for manual UI updates

4. **Post Editing Phase**
   - Allow editing of post content (titles, content, user input)
   - Provide translation functionality between languages
   - Update WeChat/Medium selection with automatic UI refresh
   - Edit labels, links, and media elements

5. **Report Generation Phase**
   - Save report to JSON file
   - Generate platform-specific markdown reports
   - Download post images to appropriate directories

## Error Handling Strategy

1. **File Operations**
   - Use try/except blocks around all file operations
   - Print detailed error messages and full stack traces
   - Provide user-friendly error notifications via Streamlit

2. **Translation Operations**
   - Use spinners to indicate processing
   - Handle API errors gracefully
   - Provide visual feedback on translation completion

3. **State Management**
   - Use session state flags to track changes
   - Trigger page reruns when UI state changes
   - Provide manual refresh option for edge cases

## Command Line Interface

- **Implementation**: argparse (with future Typer migration)
- **Required Arguments**:
  - `--start-date`: YYYY-MM-DD format (start of report period)
  - `--end-date`: YYYY-MM-DD format (end of report period)
  - `--input-dir`: Directory containing email dumps
- **Optional Flags**:
  - `--overwrite`: Force overwrite existing report
  - `--verbose`: Enable detailed console output

## Performance Optimizations

1. **UI Responsiveness**
   - Filter operations happen in memory without reload
   - Session state preserves user edits across interactions
   - Immediate feedback for platform selection changes

2. **File Operations**
   - Efficient directory traversal for email loading
   - Error handling with graceful fallbacks
   - Progress indicators for long-running operations

3. **User Experience**
   - Modular UI components for maintainability
   - Consistent styling and layout
   - Helpful error messages and operation feedback

## Security Implementation

### File Operations
- Validate file paths
- Check file permissions
- Sanitize file names

### API Security
- Secure API key storage in .env
- Validate API responses
- Handle timeouts properly

### Input Validation
- Validate all user inputs
- Sanitize file contents
- Check data integrity
