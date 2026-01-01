import logging
from tkinter import image_names
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import QnALog
from .services import analyze_qna, check_similarity_and_get_answer
from core.exceptions import EmptyAiAnswerError
logger =logging.getLogger(__name__)
class QnABotAPIView(APIView):
    def post(self, request):
        logger.info("🔥 QnABotAPIView POST CALLED")
        question_text = request.data.get('question_text')
        image = request.FILES.get('image')

        if not question_text:
            return Response({"error": "question_text required"}, status=400)

        similar = check_similarity_and_get_answer(question_text)

        if similar:
            similar.hit_count += 1
            similar.save()

            if similar.is_verified and similar.notion_page_url:
                return Response({
                    "status": "verified",
                    "Log_id": similar.id,
                    "notion_url": similar.notion_page_url,
                })

            return Response({
                "status": "duplicate",
                "Log_id": similar.id,
                "ai_answer": similar.ai_answer,
            })
        # 신규 질문 생성
        log = QnALog.objects.create(
            question_text=question_text,
            image=image,
            title=f"검토 대기 중인 질문"
        )

        image_path = log.image.path if log.image else None
        ai_result = analyze_qna(question_text, image_path)

        if not ai_result:
          return Response({"error": "AI failed"}, status=500)

        # 결과 저장
        log.ai_answer = ai_result
        log.save()

        return Response({
            "status" : "new",
            "Log_id" : log.id,
        "ai_answer" : ai_result
        })