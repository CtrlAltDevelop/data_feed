from datetime import datetime
from typing import List

from ninja import Schema


class PostRes(Schema):
    id: int
    source_id: int
    url: str
    title: str | None
    content: str | None
    metadata: dict
    is_processed: bool
    created_at: datetime
    updated_at: datetime


class PaginationRes(Schema):
    items: List[PostRes]
    count: int
    total_pages: int
    current_page: int
    has_next: bool
    has_prev: bool
    page_size: int
