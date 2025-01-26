import os
import json
import streamlit as st
import datetime
from typing import Dict, List, Optional
import webbrowser
import requests
from delorean import Delorean
from pydantic import BaseModel, field_validator, Field, field_serializer

class WeeklyPost(BaseModel):
    """A post in the weekly report."""
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
    def validate_boolean(cls, v):
        if isinstance(v, str):
            return v.lower() == "true"
        return bool(v)

class WeeklyReport(BaseModel):
    """A weekly report containing multiple posts."""
    start_date: str
    end_date: str
    week_number: int
    summary: str = ""
    posts: list[WeeklyPost] = Field(default_factory=list)

def get_week_number(date_str: str) -> int:
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.strftime("%V"))

def load_analyzed_emails(input_dir: str, start_date: str, end_date: str) -> List[Dict]:
    emails = []
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    
    for year in range(start_dt.year, end_dt.year + 1):
        year_dir = os.path.join(input_dir, str(year))
        if not os.path.exists(year_dir):
            continue
            
        for month in range(1, 13):
            if year == start_dt.year and month < start_dt.month:
                continue
            if year == end_dt.year and month > end_dt.month:
                continue
                
            month_dir = os.path.join(year_dir, f"{month:02d}")
            if not os.path.exists(month_dir):
                continue
                
            for day in range(1, 32):
                if year == start_dt.year and month == start_dt.month and day < start_dt.day:
                    continue
                if year == end_dt.year and month == end_dt.month and day > end_dt.day:
                    continue
                    
                day_dir = os.path.join(month_dir, f"{day:02d}")
                if not os.path.exists(day_dir):
                    continue
                
                for file in os.listdir(day_dir):
                    if file.endswith("_analyzed.json"):
                        with open(os.path.join(day_dir, file), 'r', encoding='utf-8') as f:
                            email_data = json.load(f)
                            emails.append(email_data)
    
    return emails

def convert_to_weekly_post(email_data: dict) -> WeeklyPost:
    """Convert an analyzed email to a WeeklyPost."""
    print(email_data)
    if isinstance(email_data['post_labels'], str):
        email_data['post_labels'] = json.loads(email_data['post_labels'])
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

def download_image(url: str, save_path: str):
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return False

def generate_markdown_report(report: WeeklyReport, is_wechat: bool) -> str:
    """Generate a markdown report for WeChat or Medium."""
    posts = [p for p in report.posts if (p.wechat_selected if is_wechat else p.medium_selected)]
    
    # Group posts by labels
    posts_by_labels = {}
    for post in posts:
        labels_key = ", ".join(sorted(post.post_labels))
        if not labels_key:
            labels_key = "Uncategorized"
        if labels_key not in posts_by_labels:
            posts_by_labels[labels_key] = []
        posts_by_labels[labels_key].append(post)
    
    # Generate markdown content
    content = []
    for labels, group_posts in posts_by_labels.items():
        #content.append(f"## {labels}")
        labels_list = labels.split(", ")
        labels_md = '， '.join([f"**{label.strip()}**" for label in labels_list])
        #content.append(labels_md)
        
        for post in group_posts:
            if is_wechat:
                content.extend([
                    f"## ({posts.index(post) + 1}/{len(posts)}) {post.title_cn}",
                    f"{labels_md}",
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
                content.extend([
                    f"### {post.title_en}",
                    "",
                    post.post_content_en,
                    "",
                    f"![]({post.main_image})" if post.main_image else "",
                    "",
                    post.user_input_en if post.user_input_en else "",
                    ""
                ])
        content.append("")
    
    return "\n".join(line for line in content if line is not None)

def run_app(input_dir: str, start_date: str, end_date: str, overwrite: bool = False):
    """Run the Streamlit app with the given parameters."""
    st.set_page_config(layout="wide", page_title="Weekly Report Editor")
    
    # Initialize session state
    if 'report' not in st.session_state:
        st.session_state.report = None
    if 'wechat_count' not in st.session_state:
        st.session_state.wechat_count = 0
    if 'medium_count' not in st.session_state:
        st.session_state.medium_count = 0
    
    # Calculate target file path
    week_number = get_week_number(end_date)
    year = end_date.split("-")[0]
    weekly_dir = os.path.join(input_dir, year, "weekly")
    os.makedirs(weekly_dir, exist_ok=True)
    target_file = os.path.join(weekly_dir, f"week_{week_number:02d}.json")
    
    # Load or create report
    if st.session_state.report is None:
        if os.path.exists(target_file) and not overwrite:
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                    report = WeeklyReport(**report_data)
                    # Update session state counts
                    st.session_state.wechat_count = len([p for p in report.posts if p.wechat_selected])
                    st.session_state.medium_count = len([p for p in report.posts if p.medium_selected])
                    st.sidebar.success(f"Loaded existing report from {target_file}")
            except Exception as e:
                print(f"Error loading report: {str(e)}")
                import traceback
                print(traceback.format_exc())
                st.sidebar.error(f"Error loading report: {str(e)}")
                # Create new report
                analyzed_emails = load_analyzed_emails(input_dir, start_date, end_date)
                posts = [convert_to_weekly_post(email) for email in analyzed_emails]
                report = WeeklyReport(
                    start_date=start_date,
                    end_date=end_date,
                    week_number=week_number,
                    posts=posts
                )
                st.sidebar.info(f"Created new report with {len(posts)} posts")
        else:
            analyzed_emails = load_analyzed_emails(input_dir, start_date, end_date)
            posts = [convert_to_weekly_post(email) for email in analyzed_emails]
            report = WeeklyReport(
                start_date=start_date,
                end_date=end_date,
                week_number=week_number,
                posts=posts
            )
            st.sidebar.info(f"Created new report with {len(posts)} posts")
        st.session_state.report = report
    else:
        report = st.session_state.report
    
    # Sidebar
    with st.sidebar:
        st.title("Weekly Report Editor")
        st.markdown(f"""
        * **Date Range**: {start_date} to {end_date}
        * **Week Number**: {get_week_number(end_date):02d}
        * **Input Directory**: {input_dir}
        """)
        
        st.markdown("---")
        
        # Summary section
        st.header("Weekly Summary")
        report.summary = st.text_area("Summary (supports Markdown)", value=report.summary, height=200)
        
        st.markdown("---")
        
        # Stats section
        st.header("Report Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Posts", len(report.posts))
        with col2:
            st.metric("WeChat", st.session_state.wechat_count)
        with col3:
            st.metric("Medium", st.session_state.medium_count)
        
        st.markdown("---")
        
        # Action buttons
        st.header("Actions")
        
        # Save button
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
                import traceback
                print(traceback.format_exc())
                st.error(f"Error saving report: {str(e)}")
        
        # Other actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button(" Download Images", use_container_width=True):
                progress = st.progress(0)
                success_count = 0
                total_images = sum(1 for p in report.posts if p.main_image)
                
                for i, post in enumerate(report.posts):
                    if post.main_image:
                        try:
                            parsed_date = datetime.datetime.fromisoformat(post.post_datetime)
                            date = Delorean(datetime=parsed_date).datetime
                            img_dir = os.path.join(input_dir, f"{date.year}", f"{date.month:02d}", f"{date.day:02d}")
                            os.makedirs(img_dir, exist_ok=True)
                            img_path = os.path.join(img_dir, f"{post.email_id}_main_image.jpg")
                            if download_image(post.main_image, img_path):
                                success_count += 1
                                print(f"Downloaded image for {post.email_id} to {img_path}")
                            progress.progress((i + 1) / total_images)
                        except Exception as e:
                            print(f"Error downloading image for {post.email_id}: {str(e)}")
                            import traceback
                            print(traceback.format_exc())
                
                st.success(f"Downloaded {success_count} of {total_images} images")
        
        with col2:
            if st.button(" WeChat Report", use_container_width=True):
                md_content = generate_markdown_report(report, True)
                md_file = os.path.join(os.path.dirname(target_file), f"week_{week_number:02d}-wechat-report.md")
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                st.success(f"Generated WeChat report")
        
        if st.button(" Medium Report", use_container_width=True):
            md_content = generate_markdown_report(report, False)
            md_file = os.path.join(os.path.dirname(target_file), f"week_{week_number:02d}-medium-report.md")
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            st.success(f"Generated Medium report")
    
    # Main area - Posts
    st.header("Email Posts")
    
    # Display each post
    for i, post in enumerate(report.posts):
        # Create a card-like container for each post
        with st.container():
            # Post header with selection status
            header_cols = st.columns([6, 2, 2])
            with header_cols[0]:
                st.subheader(f"Post {i+1}: {post.title_cn}")
            with header_cols[1]:
                prev_wechat = post.wechat_selected
                post.wechat_selected = st.checkbox(" WeChat", value=post.wechat_selected, key=f"wechat_{i}")
                if post.wechat_selected != prev_wechat:
                    st.session_state.wechat_count += (1 if post.wechat_selected else -1)
                    st.rerun()
            with header_cols[2]:
                prev_medium = post.medium_selected
                post.medium_selected = st.checkbox(" Medium", value=post.medium_selected, key=f"medium_{i}")
                if post.medium_selected != prev_medium:
                    st.session_state.medium_count += (1 if post.medium_selected else -1)
                    st.rerun()
            
            # Post metadata
            meta_cols = st.columns([1, 1])
            with meta_cols[0]:
                st.text(f"Email ID: {post.email_id}")
            with meta_cols[1]:
                st.text(f"Post Datetime: {post.post_datetime}")
            
            # Content columns
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### Chinese Content")
                post.title_cn = st.text_input(f"Title (CN) #{i}", value=post.title_cn)
                post.post_content_cn = st.text_area(f"Content (CN) #{i}", value=post.post_content_cn, height=200)
                post.user_input_cn = st.text_area(f"User Input (CN) #{i}", value=post.user_input_cn, height=100)
            
            with col2:
                st.markdown("##### English Content")
                post.title_en = st.text_input(f"Title (EN) #{i}", value=post.title_en)
                post.post_content_en = st.text_area(f"Content (EN) #{i}", value=post.post_content_en, height=200)
                post.user_input_en = st.text_area(f"User Input (EN) #{i}", value=post.user_input_en, height=100)
            
            # Labels and Links
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### Labels")
                labels_str = st.text_area(f"Labels #{i} (one per line)", value="\n".join(post.post_labels), height=100)
                post.post_labels = [label.strip() for label in labels_str.split("\n") if label.strip()]
            
            with col2:
                st.markdown("##### Links")
                links_str = st.text_area(f"Links #{i} (one per line)", value="\n".join(post.link_lists), height=100)
                post.link_lists = [link.strip() for link in links_str.split("\n") if link.strip()]
                
                # Display clickable links
                if post.link_lists:
                    st.markdown("**Clickable Links:**")
                    for link in post.link_lists:
                        st.markdown(f"[{link}]({link})")
            
            # Main Image
            st.markdown("##### Main Image")
            post.main_image = st.text_input(f"Image URL #{i}", value=post.main_image)
            if post.main_image:
                st.image(post.main_image, caption="Main Image", use_container_width=True)
            
            # Main Link
            st.markdown("##### Main Link")
            post.main_link = st.text_input(f"Main Link #{i}", value=post.main_link)
            
            # Visual separator between posts
            st.markdown("---")

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Weekly Report Editor")
    parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD format")
    parser.add_argument("--input-dir", required=True, help="Directory containing email dumps")
    parser.add_argument("--overwrite", action="store_true", help="Whether to overwrite existing files")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    run_app(args.input_dir, args.start_date, args.end_date, args.overwrite)
