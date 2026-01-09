import logging
import os
from tkinter import image_names
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import QnALog
from .services import analyze_qna, check_similarity_and_get_answer, extract_category_answer
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

            logger.info(f"🔍 유사 질문 발견: ID={similar.id}, is_verified={similar.is_verified}, notion_url={similar.notion_page_url}")

            if similar.is_verified:
                notion_url = similar.notion_page_url or os.getenv("NOTION_BOARD_URL")

                logger.info(f"✅ verified 상태, 노션 URL 반환: {similar.notion_page_url}")
                return Response({
                    "status": "verified",
                    "Log_id": similar.id,
                    "notion_url": notion_url,
                    "ai_answer": similar.ai_answer,
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

        if ai_result is None:
          return Response({
              "status":"error",
               "ai_answer": "현재 AI 서비스 이용이 원활하지 않습니다, 잠시후에 다시 시도해주세요"},
          status=503)

        extracted_cat = extract_category_answer(ai_result)
        first_line = ai_result.split("\n")[0].replace("1. **문제 요약**:", "").strip()

        # 결과 저장
        if "제목:" in ai_result:
            lines = ai_result.split("\n")
            log.title = lines[0].replace("제목:", "").strip()[:100]
            log.ai_answer = "\n".join(lines[1:]).strip()
        else:
            log.ai_answer = ai_result
            log.title = f"질문{log.id}"

        log.category =extracted_cat
        log.save()
        

        return Response({
            "status" : "new",
            "Log_id" : log.id,
            "ai_answer" : ai_result,
            "category" : extracted_cat,
        })