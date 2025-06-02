from asgiref.sync import sync_to_async
from django.core.paginator import Paginator
from ninja.errors import HttpError
from ninja.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    async def paginate_queryset(self, queryset, request, page: int, page_size: int):
        if page_size > self.max_page_size:
            return 400, {"message": f"Page size {page_size} exceeds maximum allowed ({self.max_page_size})."}

        # Create paginator with queryset
        paginator = await sync_to_async(Paginator)(queryset, page_size)

        # Check if page is valid
        total_pages = await sync_to_async(lambda: paginator.num_pages)()
        if page < 1 or page > total_pages:
            return 404, {"message": f"Page {page} not found. Valid pages are 1 to {total_pages}."}

        # Wrap synchronous get_page in sync_to_async
        page_obj = await sync_to_async(paginator.get_page)(page)

        # Wrap synchronous iteration of page_obj to get item IDs
        item_ids = await sync_to_async(lambda: [obj.id for obj in page_obj])()

        # Fetch items for the current page asynchronously
        items = await sync_to_async(list)(
            queryset.filter(id__in=item_ids).select_related('source').order_by('-created_at')
        )

        # Wrap synchronous pagination metadata access
        count = await sync_to_async(lambda: paginator.count)()
        current_page = await sync_to_async(lambda: page_obj.number)()
        has_next = await sync_to_async(lambda: page_obj.has_next())()
        has_prev = await sync_to_async(lambda: page_obj.has_previous())()

        return {
            'items': items,
            'count': count,
            'total_pages': total_pages,
            'current_page': current_page,
            'has_next': has_next,
            'has_prev': has_prev,
            'page_size': page_size,
        }
