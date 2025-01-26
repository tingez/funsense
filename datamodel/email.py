import traceback
from delorean import parse
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, InstanceOf, field_serializer, field_validator

class EmailAnalysis(BaseModel):
    """
    A Pydantic model for LLM-based email content analysis.
    This model structures the analysis of email posts with bilingual support.
    """
    email_id: str = Field(
        ..., # a must field
        description="Unique identifier for the email post"
    )

    post_labels: List[str] = Field(
        default=[],
        description="List of labels or tags associated with the email post"
    )

    post_content_cn: str = Field(
        default='',
        description="Original or translated Chinese content of the email post"
    )
    
    post_content_en: str = Field(
        default='',
        description="Original or translated English content of the email post"
    )
    
    link_lists: List[str] = Field(
        default=[],
        description="List of URLs found in the email content. Could include references, sources, or related materials"
    )
    
    post_summary_cn: str = Field(
        default='',
        description="A concise Chinese summary of the main points and key takeaways from the email"
    )
    
    post_summary_en: str = Field(
        default='',
        description="A concise English summary of the main points and key takeaways from the email",
    )
    
    post_datetime: Optional[datetime] = Field(
        default=None,
        description="The timestamp when the email was sent or received"
    )
    
    # Optional additional metadata
    source_language: Optional[str] = Field(
        None,
        description="The original language of the email content (e.g., 'en' for English, 'cn' for Chinese)"
    )
    
    confidence_score: Optional[float] = Field(
        ...,# a must field
        ge=0.0,
        le=1.0,
        description="LLM's confidence score for the analysis results (0.0 to 1.0)"
    )

    @field_serializer('post_datetime')
    def serialize_post_datetime(self, post_datetime: datetime, _info):
        if post_datetime:
            return post_datetime.isoformat()
        else:
            return post_datetime

    @field_validator('post_datetime', mode='before')
    @classmethod
    def validate_post_datetime(cls, value):
        if not value: return None
        if isinstance(value, datetime):
            return value
        try:
            return parse(value).datetime
        except Exception as e:
            print(f"Error parsing datetime: {e}")
            traceback.print_exc()
            return None

    class Config:
        """Configuration for the Pydantic model"""
        json_schema_extra_ext = {
            "example": {
                "post_content_cn": "这是一篇关于AI发展的文章，讨论了最新的进展。",
                "post_content_en": "This is an article about AI development, discussing the latest advances.",
                "link_lists": ["https://example.com/ai-research"],
                "post_summary_cn": "本文主要讨论了AI在2024年的三个主要发展方向：大模型、多模态和智能体。",
                "post_summary_en": "This article discusses three main development directions of AI in 2024: large models, multimodal, and agents.",
                "post_datetime": "2024-12-23T23:38:43",
                "source_language": "en",
                "confidence_score": 0.95
            }
        }

# Example usage:
"""
email_analysis = EmailAnalysis(
    post_content_cn="这是一篇关于AI发展的文章，讨论了最新的进展。",
    post_content_en="This is an article about AI development, discussing the latest advances.",
    link_lists=["https://example.com/ai-research"],
    post_summary_cn="本文主要讨论了AI在2024年的三个主要发展方向：大模型、多模态和智能体。",
    post_summary_en="This article discusses three main development directions of AI in 2024: large models, multimodal, and agents.",
    post_datetime=datetime.now(),
    source_language="en",
    confidence_score=0.95
)

# Validate and serialize to JSON
json_data = email_analysis.model_dump_json()
"""