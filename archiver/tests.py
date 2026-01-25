import pytest
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock

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
        fake_ai_response = """
        [메타데이터]
        제목: AI가 생성한 테스트 제목
        카테고리: Python
        키워드: 테스트, pytest,django
        
        [출력양식]
        (내용 생략)
        """
        mock_instance.generate_answer.return_value = fake_ai_response
        yield mock_instance # 테스트 함수에 이 mock_instance 전달
@pytest.fixture
def mock_notion_adapter():
    """
    NotionAdapter를 가짜로 대체하는 Fixture
    테스트 실행중 실제 Notion API 호출을 방지
    """
    with patch("archiver.services.NotionAdapter") as MockNotion:
        mock_instance = MockNotion.return_value

        mock_instance.save_to_notion.return_value = "fake-notion-page-id-123"
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

        mock_notion_adapter.save_to_notion.assert_called_once_with(created_log)


