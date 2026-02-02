import logging

from django.contrib.postgres.search import TrigramSimilarity
from django.core.files.uploadedfile import UploadedFile

from .adapters import GeminiAdapter, NotionAdapter
from .models import QnALog
from common.exceptions import AIResponseParsingError, DatabaseOperationError, ValidationError
from typing import Optional
from .adapters import qna_model_to_response_dto

logger = logging.getLogger(__name__)


class QnAService:

    def __init__(self):
        self.gemini = GeminiAdapter()
        self.notion = NotionAdapter()

    def check_similarity(self, question_text: str, threshold=0.6):
        """
        PostgreSQL의 pg_trgm을 사용하여 기존 질문들과 유사도 비교
        """
        logger.debug("============== PostgreSQL 유사도 체크 시작 ==============")

        # 1. TrigramSimilarity를 사용하여 유사도 계산 및 필터링

        similar_log = (
            QnALog.objects.annotate(
                similarity=TrigramSimilarity("question_text", question_text)
            )
            .filter(is_verified=True, similarity__gt=threshold)
            .order_by("-similarity")
            .first()
        )


        if not similar_log:
            return {
                'status': 'not_found',
                'data': None
            }

        similar_log.hit_count += 1
        similar_log.save(update_fields=["hit_count"])
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
                image_data = image.read()

            dto = self.gemini.generate_answer(question_text, image_data)



            log_obj = QnALog.objects.create(
                question_text=question_text,
                title=dto.title,
                ai_answer=dto.ai_answer,
                category=dto.category,
                keywords=dto.keywords,
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


