from rest_framework.views import exception_handler
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    # 기본 DRF 핸들러 호출
    response = exception_handler(exc, context)

    # 콘솔/Render 로그에 에러 찍기
    logger.error("❌ DRF Exception: %s", exc, exc_info=True)
    logger.error("Context: %s", context)

    # serializer 에러 상세도 확인
    if response is not None and hasattr(response, "data"):
        logger.error("Response data: %s", response.data)

    return response
