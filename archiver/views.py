import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.views import APIView
from common.exceptions import ValidationError, LLMServiceError, AIResponseParsingError, DatabaseOperationError
from .services import QnAService
from .adapters import qna_model_to_response_dto

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
            similar_log = service._check_similarity(question_text)

            if similar_log:
                if similar_log.is_verified:
                    similar_log.hit_count += 1
                    similar_log.save(update_fields=["hit_count"])
                    logger.info(f"🔍 유사 질문 발견: ID={similar_log.id}")
                # 모델을 응답 DTO 변환
                response_dto = qna_model_to_response_dto(similar_log)
                # Pydantic 모델을 dict로 변환하여 응답
                response_data = response_dto.model_dump()


                # notion_url = similar.notion_page_url or os.getenv("NOTION_BOARD_URL", "")

                if similar_log.is_verified:
                    response_data["status"] = "verified"
                    return Response(response_data)
                response_data["status"] = "duplicate"
                return Response(response_data)


            new_log = service.process_question_flow(
                question_text=question_text,
                image=image
            )

            response_dto = qna_model_to_response_dto(new_log)
            response_data = response_dto.model_dump()
            response_data["status"] = "new"
            response_data["message"] = "AI 분석이 끝났습니다"

            return Response(response_data)

        except ValidationError as e:
            # 클라이언트 요청이 잘못된 경우
            return Response({"error": e.message}, status=400)
        except LLMServiceError as e:
            # 외부 서비스에 문제가 생긴경우
            return Response({"error": e.message}, status=503)
        except AIResponseParsingError as e:
            return Response({"error": e.message}, status=400)
        except DatabaseOperationError as e:
            # 파싱 문제인 경우
            return Response({"error": e.message}, status=500)
        except Exception as e:
            logger.error(f"알수없는 에러 발생 {e}", exc_info=True)
            return Response({"error": "알수없는 에러 발생"}, status=500)