import base64
import logging
import re
from unicodedata import category

from django.contrib.postgres.search import TrigramSimilarity
from django.core.files.uploadedfile import UploadedFile

from common import exceptions
from .adapters import GeminiAdapter, NotionAdapter
from .models import QnALog
from common.exceptions import AIResponseParsingError, DatabaseOperationError, ValidationError
from typing import Optional
from .adapters import qna_model_to_response_dto

logger = logging.getLogger(__name__)


class QnAService:
    NOTION_CATEGORIES = [
        "Git",
        "Linux",
        "DB",
        "Python",
        "Flask",
        "Django",
        "FastAPI",
        "General",
    ]

    def __init__(self):
        self.gemini = GeminiAdapter()
        self.notion = NotionAdapter()

    def check_similarity(self, question_text: str, threshold=0.6):
        """
        PostgreSQL의 pg_trgm을 사용하여 기존 질문들과 유사도 비교
        """
        logger.debug("============== PostgreSQL 유사도 체크 시작 ==============")

        # 1. TrigramSimilarity를 사용하여 유사도 계산 및 필터링

        similar_question = (
            QnALog.objects.annotate(
                similarity=TrigramSimilarity("question_text", question_text)
            )
            .filter(is_verified=True, similarity__gt=threshold)
            .order_by("-similarity")
            .first()
        )
        similar_log = QnALog.objects.filter(
            similarity__gt=0.7
        ).annotate(
            similarity=TrigramSimilarity("question_text", question_text)
        ).order_bt('-similarity').first()
        if not similar_log:
            return {
                'status': 'not_found',
                'data': None
            }

        # 검증된 질문인 경우
        if similar_log.is_verified:
            similar_log.hit_count += 1
            similar_log.save(update_fields=["hit_count"])
            logger.info(f" 유사 질문 발견 (검증됨): {similar_log.id}")
        else:
            logger.info(f" 유사 질문 발견 (검토 대기중): {similar_log.id}")

        # DTO 변환
        response_dto = qna_model_to_response_dto(similar_log)
        response_data = response_dto.model_dump()

        # status 추가
        response_data["status"] = "similar_found"

        return {
           'status': 'similar_found',
            'data': response_data
        }

    def process_question_flow(self, question_text: str, image: Optional[UploadedFile] = None) -> QnALog:
        """
        이미 생성된 log_obj를 받아서 AI 분석 결과로 업데이트
        """
        try:
            if not question_text:
                raise ValidationError("질문을 입력해주세요")

            image_data = None
            if image:
                image_data = base64.b64encode(image.read()).decode('utf-8')

            dto = self.gemini.generate_answer(question_text, image_data)



            log_obj =QnALog.objects.create(
                question_text=question_text,
                answer_text=dto.ai_answer,
                category=dto.category,
                tags=dto.tags,
                image=image,
            )

            try:
                notion_page_url = self.notion.create_qna_page(log_obj)
                log_obj.notion_page_url = notion_page_url
                log_obj.save(update_fields=["notion_page_url"])
                logger.info(f"Notion 아카이빙 성공: {log_obj.id}, URL: {notion_page_url}")
            except Exception as e:
                logger.error(f"Notion 저장 실패 ID: {log_obj.id}: {e}", exc_info=True)

            return log_obj

        except (AttributeError, TypeError, IndexError) as e:
            logger.error(f"신규 질문 처리중 에러 발생 {e}")
            if 'log_obj' in locals():
                log_obj.title = "AI 응답 파싱 실패"
                log_obj.save()
            raise AIResponseParsingError("AI 응답 형식(키워드, 제목)이 형식에 맞지않습니다")
        except AIResponseParsingError:
            raise
        except Exception as e:
            logger.error(f"데이터베이스 저장 중 오류 발생: {e}", exc_info=True)
            raise DatabaseOperationError("결과를 데이터베이스에 저장하는 중 문제가 발생했습니다")

    def _build_analyze_prompt(self, question_text):
        return f"""
        너는 불필요한 설명을 하지 않는 실력파 개발 조교야.
        인사말은 생략하고 다음 구조로 핵심만 짧게 답해줘.
        [메타데이터]
        제목: (질문의 핵심 의도를 한문장으로)
        카테고리: (다음중 하나 선택 - {",".join(self.NOTION_CATEGORIES)})
        키워드: (핵심 키워드 3개를 쉼표로 구분)
        
        [출력 양식]
        제목: (질문의 핵심 의도를 한 문장으로 요약)
        1. **문제 요약**: (에러 정체 1문장)
        2. **핵심 원인**: (이유 1~2개 불렛 포인트)
        3. **해결 코드**: (중요 코드 블록. 설명은 주석으로)
        4. **체크포인트**: (실수 방지 팁 하나)

        질문 내용: {question_text}
        """
    def _parse_ai_response(self, ai_answer: str) -> dict:
        """AI응답에서 메타데이터와 본문 추출"""
        # 제목 추출
        try:
            title_match = re.search(r"제목:\s*(.*)", ai_answer)
            title = title_match.group(1).strip() if title_match else "신규 질문"

            # 카테고리 추출
            category_match = re.search(r"카테고리:\s*(.*)", ai_answer)
            category = "General"
            if category_match:
                cat_text = category_match.group(1).strip()
                for cat in self.NOTION_CATEGORIES:
                    if cat.lower() in cat_text.lower():
                        category = cat
                        break
            # 키워드 추출
            keywords_match = re.search(r"키워드:\s*(.*?)(?=\n|\[)", ai_answer, re.DOTALL)
            keywords = []
            if keywords_match:
                keywords_str = keywords_match.group(1).strip()
                keywords = [k.strip() for k in keywords_match.group(1).split(",") if k.strip()]

            return {
                "title": title,
                "category": category,
                "keywords": keywords,
                "ai_answer":ai_answer
            }
        except Exception as e:
            logger.error(f" AI 응답 파싱 실패 {e}")
            raise AIResponseParsingError("AI 응답 형식 파싱 실패")
