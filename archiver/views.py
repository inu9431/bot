from tkinter import image_names

from rest_framework.views import APIView
from rest_framework.response import Response
from .models import QnALog
from .services import analyze_qna
from core.exceptions import EmptyAiAnswerError

class QnABotAPIView(APIView):
    def post(self, request):
        question_text = request.data.get('question_text')
        image = request.FILES.get('image')

        # 데이터 기록
        log = QnALog.objects.create(
            question_text = question_text,
            image = image,
            title = f"검토 대기 중인 질문"
        )

        # AI 분석 실행
        image_path = QnALog.image.path if QnALog.image else None
        ai_result = analyze_qna(question_text, image_path)

        if not ai_result:
            raise EmptyAiAnswerError()

        # 결과 업데이트
        QnALog.ai_answer = ai_result
        QnALog.save()

        return Response({
            "status" : "success",
            "Log_id" : QnALog.id,
        "ai_answer" : ai_result
        })