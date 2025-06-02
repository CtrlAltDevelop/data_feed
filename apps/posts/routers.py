from asgiref.sync import sync_to_async

from ninja import Router, Schema

from typing import List
from django.shortcuts import get_list_or_404

from common.schemas import ErrorResponse
from .models import CrawledPost
from datetime import datetime
import asyncio

from .schemas import PaginationRes
from .services import CustomPagination

router = Router()


@router.get(
    path="",
    response={200: PaginationRes, 404: ErrorResponse, 400: ErrorResponse},
    summary="Get processed crawled posts with pagination",
    description="Retrieve a paginated list of processed crawled posts asynchronously, including pagination metadata."
)
async def get_processed_posts(request, page: int = 1, page_size: int = 20):
    """
    Retrieve processed posts with pagination asynchronously.
    Args:
        page: Page number (default: 1)
        page_size: Number of items per page (default: 20, max: 100)
    Returns:
        Paginated response with posts and metadata
    """
    queryset = CrawledPost.objects.filter(is_processed=True)
    paginator = CustomPagination()
    return await paginator.paginate_queryset(queryset=queryset, request=request, page=page, page_size=page_size)
