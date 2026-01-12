import logging
import os

from django_q.tasks import async_task
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import QnALog
from .services import QnAService

logger = logging.getLogger(__name__)


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
            question_text=question_text, image=image, title="AI 분석 중"
        )

        image_path = log.image.path if log.image else None

        # 비동기 태스크 호출
        async_task(
            "archiver.tasks.task_process_question", question_text, image_path=image_path
        )

        return Response(
            {
                "status": "processing",
                "log_id": log.id,
                "message": "새로운 질문을 접수했습니다 AI분석을 시작합니다",
            }
        )
