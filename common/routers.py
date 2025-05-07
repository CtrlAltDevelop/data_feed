from ninja import Router

import configs.api
from common.schemas.app import HealthRes

router = Router()


@router.get("health", response=HealthRes)
async def health_check(request):
    return {'status': 'ok', 'code': 200, 'version': configs.api.api_v1.version}
