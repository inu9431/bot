import logging
import re

from django.contrib.postgres.search import TrigramSimilarity
from common import exceptions
from .adapters import GeminiAdapter, NotionAdapter
from .models import QnALog
from common.exceptions import AIResponseParsingError, DatabaseOperationError
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

    def _check_similarity(self, question_text: str, threshold=0.6):
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

        if similar_question:
            logger.info(
                f"유사 질문 발견: id={similar_question.id}, similarity={similar_question.similarity:.2f}"
            )
            return similar_question

        logger.debug("유사 질문 없음 - 신규 질문으로 판정")
        return None

    def process_question_flow(self, question_text: str, image_path: str = None, log_obj:QnALog=None):
        """
        이미 생성된 log_obj를 받아서 AI 분석 결과로 업데이트
        """
        # 1. 유사도 체크 (기존 질문이 있는지)
        if log_obj is None:
            logger.error(" 서비스가 log_obj를 받지 못했습니다")
            from .models import QnALog
            log_obj = QnALog.objects.create(
                question_text=question_text,
                title = "에러 복구중"
            )


        current_image_path = log_obj.image.path if log_obj.image else None


        # 2. 신규 질문: AI 답변 생성 (GeminiAdapter 활용)
        try:
            prompt = self._build_analyze_prompt(question_text)
            ai_answer = self.gemini.generate_answer(prompt, current_image_path)

            if not ai_answer:
                raise AIResponseParsingError("Ai 답변 생성 실패")

            parsed_data = self._parse_ai_response(ai_answer)

            log_obj.title=parsed_data["title"]
            log_obj.ai_answer=parsed_data["ai_answer"]
            log_obj.category=parsed_data["category"]
            log_obj.keywords=",".join(parsed_data["keywords"])
            log_obj.save()

            logger.info(f" 로그 업데이트 완료 id: {log_obj.id}")
            return log_obj, False
        except (AttributeError, TypeError, IndexError) as e:
            logger.error(f"신규 질문 처리중 에러 발생 {e}")
            raise AIResponseParsingError("AI 응답 형식(키워드, 제목)이 형식에 맞지않습니다")
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
            category_match = re.search(r"카테고리:\s*(.*?)(?:\n$)", ai_answer)
            category = "General"
            if category_match:
                cat_text = category_match.group(1).strip()
                for cat in self.NOTION_CATEGORIES:
                    if cat.lower() in cat_text.lower():
                        category = cat
                        break
            # 키워드 추출
            keywords_match = re.search(r"키워드:\s*(.*?)(?:\n$)", ai_answer)
            keywords = []
            if keywords_match:
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
