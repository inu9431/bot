import logging
import os

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.views import APIView
from common import exceptions
from common.exceptions import ValidationError, LLMServiceError, AIResponseParsingError, DatabaseOperationError
from .models import QnALog
from .services import QnAService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class QnABotAPIView(APIView):
    def post(self, request):
        try:
            logger.info("QnABotAPIView POST called")
            question_text = request.data.get("question_text")
            image = request.FILES.get("image")

            if not question_text:
                raise ValidationError("question_text는 필수 입력값입니다")

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


            obj, _ = service.process_question_flow(question_text, log_obj=log)

            return Response(
                {
                    "status": "new",
                    "log_id": obj.id,
                    "ai_answer": obj.ai_answer,
                    "keywords": obj.keywords,
                    "message": "AI 분석이 끝났습니다",
                }
            )
        except ValidationError as e:
            # 클라이언트 요청이 잘못된 경우
            return Response({"error": e.message}, status=400)
        except LLMServiceError as e:
            # 외부 서비스에 문제가 생긴경우
            return Response({"error": e.message}, status=503)
        except (AIResponseParsingError, DatabaseOperationError) as e:
            # 파싱 문제인 경우
            return Response({"error": e.message}, status=500)
        except Exception as e:
            logger.error(f"알수없는 에러 발생 {e}", exc_info=True)
            return Response({"error": "알수없는 에러 발생"}, status=500)