import logging
import os

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import QnALog
from .services import QnAService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class QnABotAPIView(APIView):
    def post(self, request):
        logger.info("QnABotAPIView POST called")
        question_text = request.data.get("question_text")
        image = request.FILES.get("image")

        if not question_text:
            return Response({"error": "question_text required"}, status=400)

        service = QnAService()
        similar = service._check_similarity(question_text)

        if similar:
            if similar.is_verified:
                similar.hit_count += 1
                similar.save()
                logger.info(f"🔍 유사 질문 발견: ID={similar.id}")


            notion_url = similar.notion_page_url or os.getenv("NOTION_BOARD_URL", "")

            if similar.is_verified:
                return Response(
                    {
                        "status": "verified",
                        "log_id": similar.id,
                        "notion_url": notion_url,
                        "ai_answer": similar.ai_answer,
                    }
                )

            return Response(
                {
                    "status": "duplicate",
                    "log_id": similar.id,
                    "notion_url": notion_url,
                    "ai_answer": similar.ai_answer,
                }
            )

        # 신규 질문 생성 DB에 기록하고 worker 에게 던짐
        log = QnALog.objects.create(
            question_text=question_text,
            image=image,
            title="AI 분석 중",
            hit_count=0
        )
        print(f" DEBUG: 생성된 log 객체: {log}")

        obj, _ = service.process_question_flow(question_text, log)

        return Response(
            {
                "status": "new",
                "log_id": obj.id,
                "ai_answer": obj.ai_answer,
                "keywords": obj.keywords,
                "message": "AI 분석이 끝났습니다",
            }
        )
