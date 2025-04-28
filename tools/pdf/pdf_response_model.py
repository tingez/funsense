#!/usr/bin/env python3
"""
Pydantic models for PDF service response.
"""
from typing import Dict, List, Tuple, Optional, Any, Union
from pydantic import BaseModel, Field, field_serializer, field_validator


class BlockMetadata(BaseModel):
    """Metadata for block processing."""
    llm_request_count: int = Field(0, description="Number of LLM requests made")
    llm_error_count: int = Field(0, description="Number of LLM errors encountered")
    llm_tokens_used: int = Field(0, description="Number of LLM tokens used")


class PageStats(BaseModel):
    """Information about a processed page."""
    page_id: int = Field(..., description="ID of the page")
    text_extraction_method: str = Field(..., description="Method used for text extraction")
    block_counts: List[Tuple[str, int]] = Field(
        ..., 
        description="Counts of different block types"
    )
    block_metadata: BlockMetadata = Field(..., description="Metadata about block processing")

    @field_serializer('block_counts')
    def serialize_block_counts(self, block_counts: List[Tuple[str, int]]) -> List[List[Any]]:
        """Serialize block_counts to the expected format."""
        return [[block_type, count] for block_type, count in block_counts]
    
    @field_validator('block_counts', mode='before')
    def validate_block_counts(cls, v):
        """Convert block_counts from list of lists to list of tuples if needed."""
        if isinstance(v, list) and all(isinstance(item, list) and len(item) == 2 for item in v):
            return [(item[0], item[1]) for item in v]
        return v


class TableOfContentsEntry(BaseModel):
    """An entry in the table of contents."""
    title: str = Field(..., description="Title of the section")
    heading_level: Optional[int] = Field(None, description="Heading level (e.g., 1 for H1)")
    page_id: int = Field(..., description="Page ID where this section appears")
    polygon: List[List[float]] = Field(..., description="Coordinates of the section heading")


class PdfMetadata(BaseModel):
    """Metadata about the processed PDF."""
    page_stats: List[PageStats] = Field(..., description="Statistics about each page in the PDF")
    table_of_contents: List[TableOfContentsEntry] = Field([], description="Table of contents entries")
    debug_data_path: Optional[str] = Field(None, description="Path to debug data")


class PdfServiceResponse(BaseModel):
    """Complete response from the PDF service."""
    format: str = Field(..., description="Format of the content (e.g., 'markdown')")
    output: str = Field(..., description="The converted content in the specified format")
    images: Dict[str, str] = Field({}, description="Dictionary of image filename to base64-encoded image content")
    metadata: PdfMetadata = Field(..., description="Metadata about the processed PDF")
    success: bool = Field(..., description="Whether the conversion was successful")
