import logging
from django.http import JsonResponse, Http404  # Http404 추가
from django.core.exceptions import PermissionDenied
from core.exceptions import BaseAPIException

logger = logging.getLogger('apps')

class CustomExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # 1. 우리가 만든 커스텀 에러 처리
        if isinstance(exception, BaseAPIException):
            logger.warning(f"[{exception.__class__.__name__}] {exception.message}")
            return JsonResponse(
                {'status': 'fail', 'message': exception.message},
                status=exception.status_code
            )

        # 2. 장고 기본 예외(404 등)는 미들웨어가 잡지 않고 장고에게 넘깁니다.
        # 이렇게 해야 'Directory indexes are not allowed' 같은 404 에러가 500으로 변하지 않습니다.
        if isinstance(exception, (Http404, PermissionDenied)):
            return None

        # 3. 그 외 진짜 치명적인 서버 에러
        logger.error(f"Unhandled Exception: {str(exception)}", exc_info=True)
        return JsonResponse(
            {'status': 'error', 'message': '서버 내부 오류가 발생했습니다.'},
            status=500
        )