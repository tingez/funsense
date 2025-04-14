import os
import json
import streamlit as st
import datetime
from typing import Dict, List, Optional, Union, Any
import requests
from delorean import Delorean
from pydantic import BaseModel, field_validator, Field
import sys
import traceback

# Add parent directory to path for importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gmail_api.email_analyzer import translate_from_cn_to_en, translate_from_en_to_cn


class WeeklyPost(BaseModel):
    """A post in the weekly report with bilingual content."""
    email_id: str
    post_datetime: str
    title_cn: str
    title_en: str
    post_content_cn: str
    post_content_en: str
    post_labels: list[str] = Field(default_factory=list)
    link_lists: list[str] = Field(default_factory=list)
    user_input_cn: str = ""
    user_input_en: str = ""
    main_image: str = ""
    main_link: str = ""
    wechat_selected: bool = False
    medium_selected: bool = False

    @field_validator("wechat_selected", "medium_selected", mode="before")
    @classmethod
    def validate_boolean(cls, value: Any) -> bool:
        """Convert string 'true'/'false' to boolean values."""
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)


class WeeklyReport(BaseModel):
    """A weekly report containing multiple posts with metadata."""
    start_date: str
    end_date: str
    week_number: int
    summary: str = ""
    posts: list[WeeklyPost] = Field(default_factory=list)


def get_week_number(date_str: str) -> int:
    """Extract ISO week number from a date string."""
    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    return int(date_obj.strftime("%V"))


def load_analyzed_emails(input_dir: str, start_date: str, end_date: str) -> List[Dict]:
    """Load analyzed email data from JSON files within date range."""
    email_data_list = []
    start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    
    # Iterate through directory structure: year/month/day
    for year in range(start_date_obj.year, end_date_obj.year + 1):
        year_dir = os.path.join(input_dir, str(year))
        if not os.path.exists(year_dir):
            continue
            
        for month in range(1, 13):
            # Skip months outside date range
            if year == start_date_obj.year and month < start_date_obj.month:
                continue
            if year == end_date_obj.year and month > end_date_obj.month:
                continue
                
            month_dir = os.path.join(year_dir, f"{month:02d}")
            if not os.path.exists(month_dir):
                continue
                
            for day in range(1, 32):
                # Skip days outside date range
                if year == start_date_obj.year and month == start_date_obj.month and day < start_date_obj.day:
                    continue
                if year == end_date_obj.year and month == end_date_obj.month and day > end_date_obj.day:
                    continue
                    
                day_dir = os.path.join(month_dir, f"{day:02d}")
                if not os.path.exists(day_dir):
                    continue
                
                # Load all analyzed JSON files in the day directory
                for filename in os.listdir(day_dir):
                    if filename.endswith("_analyzed.json"):
                        file_path = os.path.join(day_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as file:
                                email_data = json.load(file)
                                email_data_list.append(email_data)
                        except Exception as e:
                            print(f"Error loading file {file_path}: {e}")
                            print(traceback.format_exc())
    
    return email_data_list


def convert_to_weekly_post(email_data: Dict[str, Any]) -> WeeklyPost:
    """Convert an analyzed email data dictionary to a WeeklyPost object."""
    # Parse labels if they are in string format
    if isinstance(email_data.get('post_labels'), str):
        try:
            email_data['post_labels'] = json.loads(email_data['post_labels'])
        except json.JSONDecodeError:
            email_data['post_labels'] = []
    
    # Create WeeklyPost object from email data
    return WeeklyPost(
        email_id=email_data["email_id"],
        post_datetime=email_data["post_datetime"],
        title_cn=email_data["post_summary_cn"],
        title_en=email_data["post_summary_en"],
        post_content_cn=email_data["post_content_cn"],
        post_content_en=email_data["post_content_en"],
        post_labels=email_data["post_labels"],
        link_lists=email_data["link_lists"],
        user_input_cn="",
        user_input_en="",
        main_image="",
        main_link="",
        wechat_selected=False,
        medium_selected=False
    )


def download_image(url: str, save_path: str) -> bool:
    """Download an image from a URL and save it to the specified path."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(save_path, 'wb') as file:
            file.write(response.content)
        return True
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        print(traceback.format_exc())
        return False

def _group_posts_by_labels(posts: List[WeeklyPost]) -> Dict[str, List[WeeklyPost]]:
    """Group posts by their labels for report organization."""
    posts_by_labels = {}
    for post in posts:
        # Create a sorted key of all labels for consistent grouping
        labels_key = ", ".join(sorted(post.post_labels)) or "Uncategorized"
        
        if labels_key not in posts_by_labels:
            posts_by_labels[labels_key] = []
        posts_by_labels[labels_key].append(post)
    
    return posts_by_labels


def _format_labels_markdown(labels_key: str) -> str:
    """Format labels as bold markdown text."""
    labels_list = labels_key.split(", ")
    return '， '.join([f"**{label.strip()}**" for label in labels_list])


def generate_markdown_report(report: WeeklyReport, is_wechat: bool) -> str:
    """Generate a markdown report for WeChat or Medium platforms."""
    # Filter posts based on platform selection
    selected_posts = [p for p in report.posts if (p.wechat_selected if is_wechat else p.medium_selected)]
    
    # Group posts by their labels
    grouped_posts = _group_posts_by_labels(selected_posts)
    
    # Generate markdown content
    content_blocks = []
    for labels_key, posts_in_group in grouped_posts.items():
        formatted_labels = _format_labels_markdown(labels_key)
        
        for post in posts_in_group:
            post_index = selected_posts.index(post) + 1
            total_posts = len(selected_posts)
            
            if is_wechat:
                # Chinese content for WeChat
                content_blocks.extend([
                    f"## ({post_index}/{total_posts}) {post.title_cn}",
                    formatted_labels,
                    "",
                    post.post_content_cn,
                    "",
                    f"![]({post.main_image})" if post.main_image else "",
                    "",
                    post.user_input_cn if post.user_input_cn else "",
                    "",
                    f"[{post.main_link}]({post.main_link})" if post.main_link else "",
                    ""
                ])
            else:
                # English content for Medium
                content_blocks.extend([
                    f"### {post.title_en}",
                    "",
                    post.post_content_en,
                    "",
                    f"![]({post.main_image})" if post.main_image else "",
                    "",
                    post.user_input_en if post.user_input_en else "",
                    ""
                ])
        content_blocks.append("")
    
    # Join non-None lines into final markdown
    return "\n".join(line for line in content_blocks if line is not None)


def generate_notion_report(report: WeeklyReport) -> str:
    """Generate a markdown report for Notion using English content in WeChat format."""
    # Only include posts selected for WeChat
    wechat_posts = [p for p in report.posts if p.wechat_selected]
    
    # Group posts by their labels
    grouped_posts = _group_posts_by_labels(wechat_posts)
    
    # Generate markdown content
    content_blocks = []
    for labels_key, posts_in_group in grouped_posts.items():
        # Use comma separator for English content
        labels_list = labels_key.split(", ")
        formatted_labels = ', '.join([f"**{label.strip()}**" for label in labels_list])
        
        for post in posts_in_group:
            post_index = wechat_posts.index(post) + 1
            total_posts = len(wechat_posts)
            
            content_blocks.extend([
                f"## ({post_index}/{total_posts}) {post.title_en}",
                formatted_labels,
                "",
                post.post_content_en,
                "",
                f"![]({post.main_image})" if post.main_image else "",
                "",
                post.user_input_en if post.user_input_en else "",
                "",
                f"[{post.main_link}]({post.main_link})" if post.main_link else "",
                ""
            ])
        content_blocks.append("")
    
    # Join non-None lines into final markdown
    return "\n".join(line for line in content_blocks if line is not None)

def _init_session_state() -> None:
    """Initialize Streamlit session state for tracking report data and selections."""
    if 'report' not in st.session_state:
        st.session_state.report = None
    if 'wechat_count' not in st.session_state:
        st.session_state.wechat_count = 0
    if 'medium_count' not in st.session_state:
        st.session_state.medium_count = 0


def _get_report_file_path(input_dir: str, end_date: str) -> tuple[str, int]:
    """Calculate the target file path for the weekly report and week number."""
    week_number = get_week_number(end_date)
    year = end_date.split("-")[0]
    weekly_dir = os.path.join(input_dir, year, "weekly")
    os.makedirs(weekly_dir, exist_ok=True)
    target_file = os.path.join(weekly_dir, f"week_{week_number:02d}.json")
    return target_file, week_number


def _load_existing_report(target_file: str) -> tuple[Optional[WeeklyReport], str]:
    """Load report from an existing file."""
    try:
        with open(target_file, 'r', encoding='utf-8') as report_file:
            report_data = json.load(report_file)
            report = WeeklyReport(**report_data)
            # Update session state counts
            st.session_state.wechat_count = len([p for p in report.posts if p.wechat_selected])
            st.session_state.medium_count = len([p for p in report.posts if p.medium_selected])
            return report, f"Loaded existing report from {target_file}"
    except Exception as e:
        print(f"Error loading report: {str(e)}")
        print(traceback.format_exc())
        return None, f"Error loading report: {str(e)}"


def _create_new_report(input_dir: str, start_date: str, end_date: str, week_number: int) -> tuple[WeeklyReport, str]:
    """Create a new report from analyzed emails."""
    analyzed_emails = load_analyzed_emails(input_dir, start_date, end_date)
    posts = [convert_to_weekly_post(email) for email in analyzed_emails]
    report = WeeklyReport(
        start_date=start_date,
        end_date=end_date,
        week_number=week_number,
        posts=posts
    )
    return report, f"Created new report with {len(posts)} posts"


def run_app(input_dir: str, start_date: str, end_date: str, overwrite: bool = False) -> None:
    """Run the Streamlit app with the given parameters."""
    # Configure the page layout
    st.set_page_config(layout="wide", page_title="Weekly Report Editor")
    
    # Initialize session state variables
    _init_session_state()
    
    # Get file path for report
    target_file, week_number = _get_report_file_path(input_dir, end_date)
    
    # Load or create report
    if st.session_state.report is None:
        if os.path.exists(target_file) and not overwrite:
            # Try to load existing report
            report, message = _load_existing_report(target_file)
            if report:
                st.sidebar.success(message)
                st.session_state.report = report
            else:
                # If loading fails, create new report
                st.sidebar.error(message)
                report, message = _create_new_report(input_dir, start_date, end_date, week_number)
                st.sidebar.info(message)
                st.session_state.report = report
        else:
            # Create new report
            report, message = _create_new_report(input_dir, start_date, end_date, week_number)
            st.sidebar.info(message)
            st.session_state.report = report
    else:
        # Use existing report from session state
        report = st.session_state.report
    
def _render_sidebar_header(start_date: str, end_date: str, input_dir: str) -> None:
    """Render the sidebar header with report metadata."""
    st.title("Weekly Report Editor")
    st.markdown(f"""
    * **Date Range**: {start_date} to {end_date}
    * **Week Number**: {get_week_number(end_date):02d}
    * **Input Directory**: {input_dir}
    """)
    st.markdown("---")


def _render_sidebar_summary(report: WeeklyReport) -> None:
    """Render the weekly summary section."""
    st.header("Weekly Summary")
    report.summary = st.text_area("Summary (supports Markdown)", value=report.summary, height=200)
    st.markdown("---")


def _render_sidebar_filters() -> tuple[list, list, str]:
    """Render post filter controls and return filter selections."""
    st.header("Filters")
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        platform_filter = st.multiselect(
            "Platform",
            ["All", "WeChat", "Medium", "Future"],
            default=["All"],
            key="platform_filter",
            help="Select platforms to filter posts"
        )

    with filter_col2:
        content_filter = st.multiselect(
            "Content",
            ["All", "Has Image", "Has Link", "Has CN", "Has EN"],
            default=["All"],
            key="content_filter",
            help="Filter by content type"
        )

    with filter_col3:
        date_range_filter = st.radio(
            "Date Range",
            ["All Time", "Last 24h", "Last Week"],
            key="date_filter",
            help="Filter posts by date range"
        )
        
    return platform_filter, content_filter, date_range_filter


def _apply_platform_filter(posts: List[WeeklyPost], platform_filter: List[str]) -> List[WeeklyPost]:
    """Apply platform-based filtering to posts."""
    if "All" in platform_filter:
        return posts
    
    filtered_dict = {}  # Use dict to maintain uniqueness by email_id
    
    if "WeChat" in platform_filter:
        for post in posts:
            if post.wechat_selected:
                filtered_dict[post.email_id] = post
                
    if "Medium" in platform_filter:
        for post in posts:
            if post.medium_selected:
                filtered_dict[post.email_id] = post
                
    if "Future" in platform_filter:
        # Posts not selected for any platform yet
        for post in posts:
            if not (post.wechat_selected or post.medium_selected):
                filtered_dict[post.email_id] = post
                
    return list(filtered_dict.values())


def _apply_content_filter(posts: List[WeeklyPost], content_filter: List[str]) -> List[WeeklyPost]:
    """Apply content-based filtering to posts."""
    if "All" in content_filter:
        return posts
    
    filtered_dict = {}  # Use dict to maintain uniqueness by email_id
    
    if "Has Image" in content_filter:
        for post in posts:
            if post.main_image:
                filtered_dict[post.email_id] = post
                
    if "Has Link" in content_filter:
        for post in posts:
            if post.main_link or post.link_lists:
                filtered_dict[post.email_id] = post
                
    if "Has CN" in content_filter:
        for post in posts:
            if post.title_cn.strip() or post.post_content_cn.strip():
                filtered_dict[post.email_id] = post
                
    if "Has EN" in content_filter:
        for post in posts:
            if post.title_en.strip() or post.post_content_en.strip():
                filtered_dict[post.email_id] = post
                
    return list(filtered_dict.values())


def _apply_date_filter(posts: List[WeeklyPost], date_range_filter: str) -> List[WeeklyPost]:
    """Apply date-based filtering to posts."""
    if date_range_filter == "All Time":
        return posts
    
    current_time = datetime.datetime.now()
    time_threshold = 24 * 3600 if date_range_filter == "Last 24h" else 7 * 24 * 3600  # Seconds in a day or week
    
    return [
        post for post in posts
        if (current_time - datetime.datetime.fromisoformat(post.post_datetime)).total_seconds() < time_threshold
    ]


def _render_sidebar_stats(report: WeeklyReport, filtered_posts: List[WeeklyPost]) -> None:
    """Render statistics about the filtered posts."""
    st.header("Report Statistics")
    
    # First row of stats
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Posts", len(report.posts))
    with col2:
        st.metric("Filtered Posts", len(filtered_posts))
    with col3:
        st.metric("WeChat", len([p for p in filtered_posts if p.wechat_selected]))
    with col4:
        st.metric("Medium", len([p for p in filtered_posts if p.medium_selected]))
    with col5:
        st.metric("Future", len([p for p in filtered_posts if not (p.wechat_selected or p.medium_selected)]))

    # Second row of stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("With Images", len([p for p in filtered_posts if p.main_image]))
    with col2:
        st.metric("With Links", len([p for p in filtered_posts if p.main_link or p.link_lists]))
    with col3:
        st.metric("CN Content", len([p for p in filtered_posts if p.title_cn.strip() or p.post_content_cn.strip()]))
    with col4:
        st.metric("EN Content", len([p for p in filtered_posts if p.title_en.strip() or p.post_content_en.strip()]))
    
    st.markdown("---")

def _render_sidebar_actions(report: WeeklyReport, target_file: str, week_number: int, input_dir: str) -> None:
    """Render action buttons in the sidebar."""
    st.header("Actions")

    # Save report button
    if st.button(" Save Report", type="primary", use_container_width=True):
        try:
            report_dict = report.model_dump()
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, ensure_ascii=False, indent=2)
            st.success("Saved report successfully!")
            print(f"Saved report to {target_file}")
            # Force reload of the report
            st.session_state.report = None
            st.rerun()
        except Exception as e:
            print(f"Error saving report: {str(e)}")
            print(traceback.format_exc())
            st.error(f"Error saving report: {str(e)}")

    # Download images and generate WeChat report
    col1, col2 = st.columns(2)
    with col1:
        if st.button(" Download Images", use_container_width=True):
            _download_post_images(report.posts, input_dir)
    
    with col2:
        if st.button(" WeChat Report", use_container_width=True):
            _generate_platform_report(report, target_file, week_number, platform="wechat")

    # Generate other platform reports
    if st.button(" Medium Report", use_container_width=True):
        _generate_platform_report(report, target_file, week_number, platform="medium")
        
    if st.button(" Notion Report", use_container_width=True, 
               help="Generate English version of WeChat report for Notion"):
        _generate_platform_report(report, target_file, week_number, platform="notion")


def _download_post_images(posts: List[WeeklyPost], input_dir: str) -> None:
    """Download images from posts and save them to appropriate directories."""
    progress = st.progress(0)
    success_count = 0
    total_images = sum(1 for post in posts if post.main_image)
    
    for i, post in enumerate(posts):
        if post.main_image:
            try:
                # Get date from post datetime and create directory structure
                parsed_date = datetime.datetime.fromisoformat(post.post_datetime)
                date = Delorean(datetime=parsed_date).datetime
                img_dir = os.path.join(input_dir, f"{date.year}", f"{date.month:02d}", f"{date.day:02d}")
                os.makedirs(img_dir, exist_ok=True)
                
                # Download and save the image
                img_path = os.path.join(img_dir, f"{post.email_id}_main_image.jpg")
                if download_image(post.main_image, img_path):
                    success_count += 1
                    print(f"Downloaded image for {post.email_id} to {img_path}")
                
                # Update progress bar
                progress.progress((i + 1) / total_images if total_images > 0 else 1.0)
            except Exception as e:
                print(f"Error downloading image for {post.email_id}: {str(e)}")
                print(traceback.format_exc())
    
    st.success(f"Downloaded {success_count} of {total_images} images")


def _generate_platform_report(report: WeeklyReport, target_file: str, week_number: int, platform: str) -> None:
    """Generate a markdown report for a specified platform."""
    try:
        # Generate markdown content based on platform
        if platform == "notion":
            md_content = generate_notion_report(report)
        elif platform == "wechat":
            md_content = generate_markdown_report(report, is_wechat=True)
        elif platform == "medium":
            md_content = generate_markdown_report(report, is_wechat=False)
        else:
            st.error(f"Unknown platform: {platform}")
            return
        
        # Save the report to file
        report_dir = os.path.dirname(target_file)
        md_file = os.path.join(report_dir, f"week_{week_number:02d}-{platform}-report.md")
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
            
        st.success(f"Generated {platform.capitalize()} report")
        print(f"Saved {platform} report to {md_file}")
    except Exception as e:
        st.error(f"Error generating {platform} report: {str(e)}")
        print(f"Error generating {platform} report: {str(e)}")
        print(traceback.format_exc())

def _render_post_header(post: WeeklyPost, index: int, post_key: str) -> None:
    """Render post header with title and platform selection controls."""
    # Create columns for title and platform selection
    header_cols = st.columns([6, 2, 2])
    
    # Title column
    with header_cols[0]:
        st.subheader(f"Post {index+1}: {st.session_state[post_key].title_cn}")
    
    # Create wechat_changed and medium_changed flags if they don't exist
    if f"wechat_changed_{post.email_id}" not in st.session_state:
        st.session_state[f"wechat_changed_{post.email_id}"] = False
    if f"medium_changed_{post.email_id}" not in st.session_state:
        st.session_state[f"medium_changed_{post.email_id}"] = False
    
    # Create function to update the actual report object from session state
    def update_report_post(post_id):
        # Find the actual post in the report to update it from session state
        for i, report_post in enumerate(st.session_state.report.posts):
            if report_post.email_id == post_id:
                # Update the report post from session state
                for attr in vars(st.session_state[post_key]):
                    if hasattr(report_post, attr):
                        setattr(report_post, attr, getattr(st.session_state[post_key], attr))
                break
        
    # WeChat selection column
    with header_cols[1]:
        prev_wechat = st.session_state[post_key].wechat_selected
        # Ensure unique key by combining the index with email_id
        wechat_selected = st.checkbox(" WeChat", value=prev_wechat, key=f"wechat_{post.email_id}_{index}")
        if wechat_selected != prev_wechat:
            # Update session state counter for statistics
            st.session_state.wechat_count += (1 if wechat_selected else -1)
            
            # Update session state post
            st.session_state[post_key].wechat_selected = wechat_selected
            
            # Update the actual post in the report
            update_report_post(post.email_id)
            
            print(f"WeChat selection changed for post {post.email_id}: {wechat_selected}")
            st.session_state[f"wechat_changed_{post.email_id}_{index}"] = True
            st.rerun()
    
    # Medium selection column
    with header_cols[2]:
        prev_medium = st.session_state[post_key].medium_selected
        # Ensure unique key by combining the index with email_id
        medium_selected = st.checkbox(" Medium", value=prev_medium, key=f"medium_{post.email_id}_{index}")
        if medium_selected != prev_medium:
            # Update session state counter for statistics
            st.session_state.medium_count += (1 if medium_selected else -1)
            
            # Update session state post
            st.session_state[post_key].medium_selected = medium_selected
            
            # Update the actual post in the report
            update_report_post(post.email_id)
            
            print(f"Medium selection changed for post {post.email_id}: {medium_selected}")
            st.session_state[f"medium_changed_{post.email_id}_{index}"] = True
            st.rerun()

    # Post metadata
    meta_cols = st.columns([1, 1])
    with meta_cols[0]:
        st.text(f"Email ID: {post.email_id}")
    with meta_cols[1]:
        st.text(f"Post Datetime: {post.post_datetime}")


def _render_post_content(post: WeeklyPost, index: int, post_key: str) -> None:
    """Render post content with translation buttons and input fields."""
    # Content columns
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Chinese Content")
        title_cn = st.text_input(f"Title (CN) #{post.email_id}",
                                value=st.session_state[post_key].title_cn,
                                key=f"title_cn_{post.email_id}")
        st.session_state[post_key].title_cn = title_cn

        # Title translation buttons
        title_cols = st.columns([1, 1])
        with title_cols[0]:
            if st.button("→ Translate Title to EN", key=f"translate_title_cn_to_en_{post.email_id}",
                        help="Translate Chinese title to English"):
                with st.spinner("Translating..."):
                    st.session_state[post_key].title_en = translate_from_cn_to_en(st.session_state[post_key].title_cn)
                    st.rerun()

        post_content_cn = st.text_area(f"Content (CN) #{post.email_id}",
                                      value=st.session_state[post_key].post_content_cn,
                                      height=200,
                                      key=f"content_cn_{post.email_id}")
        st.session_state[post_key].post_content_cn = post_content_cn

        # Content translation buttons
        content_cols = st.columns([1, 1])
        with content_cols[0]:
            if st.button("→ Translate Content to EN", key=f"translate_content_cn_to_en_{post.email_id}",
                        help="Translate Chinese content to English"):
                with st.spinner("Translating..."):
                    st.session_state[post_key].post_content_en = translate_from_cn_to_en(st.session_state[post_key].post_content_cn)
                    st.rerun()

        user_input_cn = st.text_area(f"User Input (CN) #{post.email_id}",
                                    value=st.session_state[post_key].user_input_cn,
                                    height=100,
                                    key=f"user_input_cn_{post.email_id}")
        st.session_state[post_key].user_input_cn = user_input_cn

        # User input translation buttons
        input_cols = st.columns([1, 1])
        with input_cols[0]:
            if st.button("→ Translate Input to EN", key=f"translate_input_cn_to_en_{post.email_id}",
                        help="Translate Chinese user input to English"):
                with st.spinner("Translating..."):
                    st.session_state[post_key].user_input_en = translate_from_cn_to_en(st.session_state[post_key].user_input_cn)
                    st.rerun()

        # All-in-one translation button
        if st.button("→ Translate ALL to EN", key=f"translate_all_cn_to_en_{post.email_id}",
                    use_container_width=True,
                    help="Translate all Chinese content to English"):
            with st.spinner("Translating all content..."):
                st.session_state[post_key].title_en = translate_from_cn_to_en(st.session_state[post_key].title_cn)
                st.session_state[post_key].post_content_en = translate_from_cn_to_en(st.session_state[post_key].post_content_cn)
                st.session_state[post_key].user_input_en = translate_from_cn_to_en(st.session_state[post_key].user_input_cn)
                st.rerun()

    with col2:
        st.markdown("##### English Content")
        title_en = st.text_input(f"Title (EN) #{post.email_id}",
                                value=st.session_state[post_key].title_en,
                                key=f"title_en_{post.email_id}")
        st.session_state[post_key].title_en = title_en

        # Title translation buttons
        title_cols = st.columns([1, 1])
        with title_cols[0]:
            if st.button("← Translate Title to CN", key=f"translate_title_en_to_cn_{post.email_id}",
                        help="Translate English title to Chinese"):
                with st.spinner("Translating..."):
                    st.session_state[post_key].title_cn = translate_from_en_to_cn(st.session_state[post_key].title_en)
                    st.rerun()

        post_content_en = st.text_area(f"Content (EN) #{post.email_id}",
                                      value=st.session_state[post_key].post_content_en,
                                      height=200,
                                      key=f"content_en_{post.email_id}")
        st.session_state[post_key].post_content_en = post_content_en

        # Content translation buttons
        content_cols = st.columns([1, 1])
        with content_cols[0]:
            if st.button("← Translate Content to CN", key=f"translate_content_en_to_cn_{post.email_id}",
                        help="Translate English content to Chinese"):
                with st.spinner("Translating..."):
                    st.session_state[post_key].post_content_cn = translate_from_en_to_cn(st.session_state[post_key].post_content_en)
                    st.rerun()

        user_input_en = st.text_area(f"User Input (EN) #{post.email_id}",
                                    value=st.session_state[post_key].user_input_en,
                                    height=100,
                                    key=f"user_input_en_{post.email_id}")
        st.session_state[post_key].user_input_en = user_input_en

        # User input translation buttons
        input_cols = st.columns([1, 1])
        with input_cols[0]:
            if st.button("← Translate Input to CN", key=f"translate_input_en_to_cn_{post.email_id}",
                        help="Translate English user input to Chinese"):
                with st.spinner("Translating..."):
                    st.session_state[post_key].user_input_cn = translate_from_en_to_cn(st.session_state[post_key].user_input_en)
                    st.rerun()

        # All-in-one translation button
        if st.button("← Translate ALL to CN", key=f"translate_all_en_to_cn_{post.email_id}",
                    use_container_width=True,
                    help="Translate all English content to Chinese"):
            with st.spinner("Translating all content..."):
                st.session_state[post_key].title_cn = translate_from_en_to_cn(st.session_state[post_key].title_en)
                st.session_state[post_key].post_content_cn = translate_from_en_to_cn(st.session_state[post_key].post_content_en)
                st.session_state[post_key].user_input_cn = translate_from_en_to_cn(st.session_state[post_key].user_input_en)
                st.rerun()
            
    # Labels and Links
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Labels")
        labels_str = st.text_area(f"Labels #{post.email_id} (one per line)",
                                 value="\n".join(st.session_state[post_key].post_labels),
                                 height=100,
                                 key=f"labels_{post.email_id}")
        st.session_state[post_key].post_labels = [label.strip() for label in labels_str.split("\n") if label.strip()]
    
    with col2:
        st.markdown("##### Links")
        links_str = st.text_area(f"Links #{post.email_id} (one per line)",
                                value="\n".join(st.session_state[post_key].link_lists),
                                height=100,
                                key=f"links_{post.email_id}")
        st.session_state[post_key].link_lists = [link.strip() for link in links_str.split("\n") if link.strip()]
        
        # Display clickable links
        if st.session_state[post_key].link_lists:
            st.markdown("**Clickable Links:**")
            for link in st.session_state[post_key].link_lists:
                st.markdown(f"[{link}]({link})")
    
    # Main Image
    st.markdown("##### Main Image")
    main_image = st.text_input(f"Image URL #{post.email_id}",
                              value=st.session_state[post_key].main_image,
                              key=f"image_{post.email_id}")
    st.session_state[post_key].main_image = main_image

    if st.session_state[post_key].main_image:
        st.image(st.session_state[post_key].main_image, caption="Main Image", use_container_width=True)
    
    # Main Link
    st.markdown("##### Main Link")
    main_link = st.text_input(f"Main Link #{post.email_id}",
                             value=st.session_state[post_key].main_link,
                             key=f"main_link_{post.email_id}")
    st.session_state[post_key].main_link = main_link

    # Update the actual post object with session state values
    for attr in vars(post):
        if hasattr(st.session_state[post_key], attr):
            setattr(post, attr, getattr(st.session_state[post_key], attr))
    
    # Visual separator between posts
    st.markdown("---")


def run_app(input_dir: str, start_date: str, end_date: str, overwrite: bool = False) -> None:
    """Run the Streamlit app with the given parameters."""
    # Configure the page layout
    st.set_page_config(layout="wide", page_title="Weekly Report Editor")
    
    # Initialize session state variables
    _init_session_state()
    
    # Get file path for report
    target_file, week_number = _get_report_file_path(input_dir, end_date)
    
    # Load or create report
    if st.session_state.report is None:
        if os.path.exists(target_file) and not overwrite:
            # Try to load existing report
            report, message = _load_existing_report(target_file)
            if report:
                st.sidebar.success(message)
                st.session_state.report = report
            else:
                # If loading fails, create new report
                st.sidebar.error(message)
                report, message = _create_new_report(input_dir, start_date, end_date, week_number)
                st.sidebar.info(message)
                st.session_state.report = report
        else:
            # Create new report
            report, message = _create_new_report(input_dir, start_date, end_date, week_number)
            st.sidebar.info(message)
            st.session_state.report = report
    else:
        # Use existing report from session state
        report = st.session_state.report
    
    # Render sidebar components
    with st.sidebar:
        _render_sidebar_header(start_date, end_date, input_dir)
        _render_sidebar_summary(report)
        platform_filter, content_filter, date_range_filter = _render_sidebar_filters()
        
        # Apply filters in sequence
        filtered_posts = report.posts
        filtered_posts = _apply_platform_filter(filtered_posts, platform_filter)
        filtered_posts = _apply_content_filter(filtered_posts, content_filter)
        filtered_posts = _apply_date_filter(filtered_posts, date_range_filter)
        
        _render_sidebar_stats(report, filtered_posts)
        _render_sidebar_actions(report, target_file, week_number, input_dir)

    # Main area - Posts
    st.header("Email Posts")
    
    # Display each post
    for i, post in enumerate(filtered_posts):
        # Create a card-like container for each post
        with st.container():
            # Use session state for this post if not already initialized
            post_key = f"post_{post.email_id}"
            if post_key not in st.session_state:
                st.session_state[post_key] = post

            # Render post components
            _render_post_header(post, i, post_key)
            _render_post_content(post, i, post_key)
    
    # Add a refresh button to manually trigger re-rendering if needed
    if st.button("Refresh View", key="refresh_view_main", use_container_width=True):
        st.rerun()


if __name__ == "__main__":
    import argparse
    
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description="Weekly Report Editor")
    parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD format")
    parser.add_argument("--input-dir", required=True, help="Directory containing email dumps")
    parser.add_argument("--overwrite", action="store_true", help="Whether to overwrite existing files")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    # Parse arguments and run the app
    args = parser.parse_args()
    run_app(args.input_dir, args.start_date, args.end_date, args.overwrite)
