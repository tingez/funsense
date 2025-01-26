from pathlib import Path
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, Page, Browser
import html2text
import time


class TwitterCrawler:
    def __init__(self, headless: bool = True):
        """Initialize Twitter crawler.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._html2text = html2text.HTML2Text()
        self._html2text.body_width = 0  # Don't wrap text

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def start(self):
        """Start the browser session."""
        logger.info("Starting browser session...")
        self.playwright = sync_playwright().start()
        
        # Configure browser with stealth settings
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )
        
        context = self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            bypass_csp=True,  # Bypass Content Security Policy
        )
        
        # Add extra headers
        context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
        })
        
        self.page = context.new_page()
        
        # Add scripts to mask automation
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        logger.info("Browser session started successfully")

    def stop(self):
        """Stop the browser session."""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser session stopped")

    def get_tweet_content(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get tweet content from a Twitter URL.
        
        Args:
            url: Twitter URL (e.g., https://x.com/username/status/123456789)
            
        Returns:
            Dictionary containing tweet content and metadata
        """
        try:
            logger.info(f"Fetching tweet from URL: {url}")
            
            # Navigate to the URL with stealth settings
            self.page.goto(url, wait_until="networkidle", timeout=30000)
            logger.debug("Page loaded successfully")
            
            # Add a small delay to let dynamic content load
            time.sleep(2)

            # Wait for the article tag with increased timeout
            article = self.page.wait_for_selector(
                "article[data-testid='tweet']", 
                timeout=20000,
                state="attached"
            )
            
            if not article:
                logger.error("Could not find tweet content")
                return None

            # Get the article HTML
            article_html = article.inner_html()
            logger.debug("Retrieved article HTML")

            # Convert HTML to markdown
            markdown_content = self._html2text.handle(article_html)
            logger.debug("Converted HTML to markdown")

            # Get tweet metadata
            tweet_text = article.text_content()
            tweet_id = url.split("/status/")[-1].split("?")[0]
            username = url.split("/")[3]

            # Extract image URLs if present
            image_urls = []
            images = article.query_selector_all("img[src*='pbs.twimg.com']")
            for img in images:
                src = img.get_attribute("src")
                if src and "profile" not in src.lower():  # Exclude profile pictures
                    image_urls.append(src)

            result = {
                "tweet_id": tweet_id,
                "username": username,
                "url": url,
                "text": tweet_text,
                "markdown": markdown_content,
                "image_urls": image_urls,
                "html": article_html
            }

            logger.info(f"Successfully retrieved tweet from {username}")
            return result

        except Exception as e:
            logger.error(f"Error fetching tweet: {str(e)}", exc_info=True)
            return None
