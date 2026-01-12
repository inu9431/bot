import logging
import os
from typing import Optional

import google.generativeai as genai
import requests
from django.conf import settings
from PIL import Image

from common.exceptions import LLMServiceError, NotionAPIError

from .dto import QnADTO

logger = logging.getLogger(__name__)


class GeminiAdapter:
    """Gemini API와 통신을 전담하는 어댑터"""

    _client_configured = False  # 클래스 변수로 설정 여부 관리

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not self.api_key:
            raise LLMServiceError("GEMINI_API_KEY가 설정되지 않았습니다")
        # do not configure client here; lazy configure in _setup_client

    def _setup_client(self):
        # Lazy Singleton: 설정이 안되있을떄만 실행
        if not GeminiAdapter._client_configured:
            api_key = self.api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise LLMServiceError("GEMINI_API_KEY missing")
            # prefer configure if available
            if hasattr(genai, "configure"):
                genai.configure(api_key=api_key)
            GeminiAdapter._client_configured = True

    def generate_answer(self, prompt: str, image_path: Optional[str] = None) -> str:
        self._setup_client()

        content_parts = []
        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                content_parts.append(img)
                logger.info(f"이미지 로딩 성공 {image_path}")
            except Exception as e:
                logger.warning(f"이미지 로딩 에러 (경로 {image_path}): {e}")

        content_parts.append(prompt)

        # prepare prompt text
        prompt_text = "\n".join([str(p) for p in content_parts])

        # Try client-based API (google-genai) first
        if hasattr(genai, "Client"):
            try:
                client = (
                    genai.Client(api_key=self.api_key)
                    if callable(getattr(genai, "Client"))
                    else genai.Client()
                )
                if hasattr(client, "responses") and hasattr(client.responses, "create"):
                    resp = client.responses.create(
                        model="models/gemini-2.5-flash", input=prompt_text
                    )
                    text = getattr(resp, "output_text", None) or getattr(
                        resp, "text", None
                    )
                    if not text:
                        out = getattr(resp, "output", None)
                        if isinstance(out, list) and out:
                            parts = []
                            for o in out:
                                if isinstance(o, dict):
                                    for c in o.get("content", []):
                                        if isinstance(c, dict) and "text" in c:
                                            parts.append(c["text"])
                            text = " ".join(parts) if parts else None
                    if text:
                        return text
            except Exception:
                # ignore and fallback to other patterns
                pass

        # Try module-level responses API
        if hasattr(genai, "responses") and hasattr(genai.responses, "create"):
            try:
                resp = genai.responses.create(
                    model="models/gemini-2.5-flash", input=prompt_text
                )
                text = (
                    getattr(resp, "output_text", None)
                    or getattr(resp, "text", None)
                    or str(resp)
                )
                if text:
                    return text
            except Exception:
                pass

        try:
            # SDK가 제공하는 generate-like API를 사용하도록 가정
            if hasattr(genai, "generate"):
                resp = genai.generate(prompt="\n".join([str(p) for p in content_parts]))
                text = getattr(resp, "text", None) or str(resp)
                if not text:
                    raise LLMServiceError("Gemini 응답 없음")
                return text
            else:
                # SDK 미설치/미지원 환경에서는 명확한 에러를 던집니다.
                raise LLMServiceError("Gemini 클라이언트 미지원")
        except Exception as e:
            msg = str(e).lower()
            if "quota" in msg or "rate" in msg:
                logger.warning(f"Quota/Rate limit error from Gemini: {e}")
                raise LLMServiceError("API 할당량 초과, 나중에 재시도하세요")
            logger.error(f"Gemini error: {e}", exc_info=True)
            raise LLMServiceError("AI 응답 생성 실패")


class NotionAdapter:
    """Notion API와 통신을 전담하는 어댑터"""

    def __init__(self):
        self.token = getattr(settings, "NOTION_TOKEN", None)
        self.database_id = getattr(settings, "NOTION_DB_ID", None)

        if not self.token or not self.database_id:
            raise NotionAPIError("NOTION_TOKEN 또는 NOTION_DB_ID가 설정되지 않았습니다")

        self.url = "https://api.notion.com/v1/pages"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def create_qna_page(self, dto: QnADTO) -> str:
        """DTO를 받아서 노션 페이지를 생성하고 생성된 페이지 URL 반환"""
        properties = {
            "이름": {"title": [{"text": {"content": (dto.title or "질문")[:100]}}]},
            "질문내용": {
                "rich_text": [
                    {"text": {"content": (dto.question_text or "내용 없음")[:1990]}}
                ]
            },
            "AI답변": {
                "rich_text": [
                    {"text": {"content": (dto.ai_answer or "답변 대기 중")[:1990]}}
                ]
            },
            "카테고리": {"select": {"name": dto.category or "General"}},
            "질문횟수": {"number": int(dto.hit_count or 1)},
        }

        # 멀티 셀렉트(키워드) 처리
        if dto.keywords:
            properties["키워드"] = {
                "multi_select": [{"name": kw[:50]} for kw in dto.keywords]
            }

        data = {"parent": {"database_id": self.database_id}, "properties": properties}

        try:
            # 타임아웃을 설정하여 무한 대기를 방지합니다
            response = requests.post(
                self.url, headers=self.headers, json=data, timeout=10
            )

            if response.status_code == 200:
                notion_url = response.json().get("url")
                logger.info(f"노션 페이지 생성 성공 {notion_url}")
                return notion_url
            else:
                error_detail = response.json()
                logger.error(f" 노션 API 에러 응답: {error_detail}")
                raise NotionAPIError(
                    f" 노션 API 에러 :{error_detail.get('message', 'unknown Error')}"
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"노션 연결 중 네트워크 오류 발생 {e}")
            raise NotionAPIError(f" 노션 서버 연결 실패 {str(e)}")
