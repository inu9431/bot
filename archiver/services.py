import logging
import re

from django.contrib.postgres.search import TrigramSimilarity

from .adapters import GeminiAdapter, NotionAdapter
from .models import QnALog

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

    def process_question_flow(self, question_text: str, image_path: str = None):
        """
        전체 흐름 제어: 유사도 체크 -> AI 분석 -> DB 저장
        (디스코드 봇이 호출하는 메인 메서드)
        """
        # 1. 유사도 체크 (기존 질문이 있는지)
        similar_obj = self._check_similarity(question_text)
        if similar_obj:
            similar_obj.hit_count += 1
            similar_obj.save()
            return similar_obj, True  # (객체, 중복여부)

        # 2. 신규 질문: AI 답변 생성 (GeminiAdapter 활용)
        try:
            prompt = self._build_analyze_prompt(question_text)
            ai_answer = self.gemini.generate_answer(prompt, image_path)

            if not ai_answer:
                raise Exception("Ai 답변 생성 실패")

            # 데이터 추출
            category = self._extract_category(ai_answer)
            title = self._extract_title(ai_answer)
            keywords = self._extract_keywords_via_ai(question_text, ai_answer)

            new_obj = QnALog.objects.create(
                question_text=question_text,
                title=title,
                ai_answer=ai_answer,
                category=category,
                keywords=",".join(keywords),
                hit_count=1,
                is_verified=False,
            )
            return new_obj, False
        except Exception as e:
            logger.error(f"신규 질문 처리중 에러 발생 {e}")
            return None, False

    def _build_analyze_prompt(self, question_text):
        return f"""
        너는 불필요한 설명을 하지 않는 실력파 개발 조교야.
        인사말은 생략하고 다음 구조로 핵심만 짧게 답해줘.

        [출력 양식]
        제목: (질문의 핵심 의도를 한 문장으로 요약)
        1. **문제 요약**: (에러 정체 1문장)
        2. **핵심 원인**: (이유 1~2개 불렛 포인트)
        3. **해결 코드**: (중요 코드 블록. 설명은 주석으로)
        4. **체크포인트**: (실수 방지 팁 하나)

        마지막에 질문 성격에 맞는 태그를 반드시 달아줘 (예: #DB, #Python).
        카테고리 리스트: {",".join(self.NOTION_CATEGORIES)}
        
        질문 내용: {question_text}
        """

    def _extract_category(self, ai_text):
        tags = re.findall(r"#(\w+)", ai_text)
        for tag in tags:
            for cat in self.NOTION_CATEGORIES:
                if tag.lower() == cat.lower():
                    return cat
        return "General"

    def _extract_title(self, ai_text):
        """제목 파싱"""
        match = re.search(r"제목:\s*(.*)", ai_text)
        return match.group(1).strip() if match else "신규 질문"

    def _extract_keywords_via_ai(self, question, answer):
        prompt = f"질문과 답변을 분석해 키워드 3개를 쉼표로 구분해줘: {question[:50]} / {answer[:50]}"
        try:
            res = self.gemini.generate_answer(prompt)
            return [k.strip() for k in res.split(",") if k.strip()]
        except:
            return []
