from rest_framework import status

class BaseAPIException(Exception):
    def __init__(self, message="오류가 발생했습니다", status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class NotionAPIError(BaseAPIException):
    """노션 서버 연동 실패 시"""
    def __init__(self, message="업로드 실패"):
        super().__init__(message=message, status_code=status.HTTP_502_BAD_GATEWAY)

class EmptyAiAnswerError(BaseAPIException):
    def __init__(self, message="AI 응답이 비어있음"):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)