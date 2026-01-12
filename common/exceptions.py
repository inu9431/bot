class BaseProjectError(Exception):
    """프로젝트 예외 클래스"""

    def __init__(self, message="오류가 발생했습니다"):
        self.message = message
        super().__init__(self.message)


class LLMServiceError(BaseProjectError):
    """Gemini API 등 AI 관련 오류"""

    pass


class NotionAPIError(BaseProjectError):
    """노션 API 전송 관련 오류"""

    pass


class SimilarityCheckError(BaseProjectError):
    """유사도 체크 과정에서의 오류"""

    pass
