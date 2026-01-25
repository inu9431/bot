import pytest
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock

from google.genai.tests.client.test_async_stream import responses

from .models import QnALog
from common.exceptions import ValidationError, LLMServiceError, AIResponseParsingError, DatabaseOperationError
@pytest.fixture
def qna_bot_api_url():
    """API 엔드포인트 URL을 제공하는 Fixture"""
    return reverse("archiver:qna_bot")


pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    """테스트용 API 클라이언트 제공하는 Fixture"""
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def qna_bot_url():
    """API 엔드포인트를 URL로 제공하는 Fixture"""
    return reverse("archiver:qna_bot")

@pytest.fixture
def mock_gemini_adapter():
    """
    GeminiAdapter 가짜로 대체하는 Fixture
    테스트 실행중 실제 AI API 호출을 방지합니다
    """
    with patch("archiver.services.GeminiAdapter") as MockGemini:
        mock_instance = MockGemini.return_value
        mock_dto = MagicMock()
        mock_dto.ai_answer = "테스트 AI 답변입니다"
        mock_dto.category = "Python"
        mock_dto.keywords = "테스트, pytest, django"
        mock_dto.title = "AI가 생성한 테스트 제목"
        mock_instance.generate_answer.return_value = mock_dto
        yield mock_instance
@pytest.fixture
def mock_notion_adapter():
    """
    NotionAdapter를 가짜로 대체하는 Fixture
    테스트 실행중 실제 Notion API 호출을 방지
    """
    with patch("archiver.services.NotionAdapter") as MockNotion:
        mock_instance = MockNotion.return_value
        mock_instance.create_qna_page.return_value = "https://notion.so/fake-page-123"
        yield mock_instance

# ==================================================================================
# 기능 테스트
# ==================================================================================

class TestQnABotAPI:
    """QnABotAPIVIEW의 주요 기능 흐름을 테스트합니다"""

    def test_new_question_flow(self, api_client, qna_bot_url, mock_gemini_adapter, mock_notion_adapter):
        """
        [통합 테스트/성공] 실규 질문 시, View-Service-DB 연동 및 AI 응답 처리 흐름을 검증
        """
        # 준비
        test_question = "새로운 통합 테스트 질문입니다"
        request_data = {"question_text": test_question}

        # 실행
        response = api_client.post(qna_bot_url, request_data, format="json")

        # 검증
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "new"

        # DB에 데이터가 올바르게 생성되었는지 검증
        assert QnALog.objects.count() == 1
        created_log = QnALog.objects.first()
        assert created_log.question_text == test_question
        assert created_log.title == "AI가 생성한 테스트 제목"
        assert "pytest" in created_log.keywords

        # 응답 데이터가 생성된 데이터와 일치하는지 검증
        assert response_data["id"] == created_log.id
        assert response_data["title"] == created_log.title

        # 외부 서비스가 올바르게 호출되었는지 검증
        mock_gemini_adapter.generate_answer.assert_called_once()

        mock_notion_adapter.create_qna_page.assert_called_once_with(created_log)

    def test_ai_response_parsing_failure(self, api_client, qna_bot_url, mock_gemini_adapter, mock_notion_adapter):
        """
        [통합 테스트] AI 응답이 예상과 다른 형식일떄, 파싱 에러를  핸들링하는지 검증
        """

        mock_gemini_adapter.generate_answer.return_value = None
        request_data = {"question_text": "AI 파싱 실패 테스트"}

        response = api_client.post(qna_bot_url, request_data, format="json")

        assert response.status_code == 400
        assert "AI 응답 형식" in response.json()["error"]

        mock_notion_adapter.create_qna_page.assert_not_called()


    def test_notion_api_failure(self, api_client, qna_bot_url, mock_gemini_adapter, mock_notion_adapter):
        """
        [통합 테스트 성공] Notion 저장에 실패하더라도, 전체 흐름은 중단되지 않고 성공 응답을 반환하는지 검증
        """
        mock_notion_adapter.create_qna_page.side_effect = Exception("Notion API 에러 발생")
        request_data = {"question_text": "Notion API 실패 테스트 질문"}

        response = api_client.post(qna_bot_url, request_data, format="json")

        # 노션 저장 실패했지만 AI응답은 성공
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "new"

        # DB저장 및 AI 분석은 정상이어야함
        assert QnALog.objects.count() == 1
        log = QnALog.objects.first()
        assert log.title == "AI가 생성한 테스트 제목"

        mock_gemini_adapter.generate_answer.assert_called_once()
        mock_notion_adapter.create_qna_page.assert_called_once()

