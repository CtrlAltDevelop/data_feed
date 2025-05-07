from ninja import Swagger, NinjaAPI

from apps.posts.routers import router as post_router
from common.routers import router as common_router


api_v1 = NinjaAPI(
    title='DataFeed API',
    description='Data Feed Api - FastAPI-Powered Trading Experience 🚀',
    version='1.0.0',
    openapi_url='/openapi.json',
    docs=Swagger(settings={
        "persistAuthorization": True,
        "defaultModelsExpandDepth": True,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "docExpansion": "none"
    })
)


api_v1.add_router("/", common_router)
api_v1.add_router("/posts", post_router, tags=["Posts"])
