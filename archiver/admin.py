import logging
from django.contrib import admin
from import_export.admin import ExportActionMixin, logger
from .models import QnALog
from .services import send_to_notion  # 아까 작성한 노션 전송 함수 가져오기
from core.exceptions import NotionAPIError, EmptyAiAnswerError

logger = logging.getLogger('apps')

@admin.register(QnALog)
class QnALogAdmin(ExportActionMixin, admin.ModelAdmin):
    # 1. 목록 화면 설정
    # is_verified(검증 완료)를 목록에 추가하여 한눈에 파악 가능
    list_display = ('title', 'short_question', 'is_verified', 'created_at')
    # 목록에서 바로 체크박스를 눌러서 저장할 수 있게 설정
    list_editable = ('is_verified',)
    list_filter = ('is_verified', 'created_at')
    search_fields = ('question_text', 'ai_answer')

    # 2. 질문 요약 표시 (기존 유지)
    def short_question(self, obj):
        return obj.question_text[:30] + "..."

    short_question.short_description = '질문 요약'

    # 3. 핵심 로직: 저장 버튼 클릭 시 실행
    def save_model(self, request, obj, form, change):
        try:
            # 1. 저장 전 기본 검증 (답변이 비어있으면 노션 전송 금지)
            if obj.is_verified and not obj.ai_answer:
                raise EmptyAiAnswerError("AI 답변이 비어있는 상태에서는 검증 완료를 할 수 없습니다.")

            # 2. 먼저 DB에 변경 사항 저장
            super().save_model(request, obj, form, change)

            # 3. '검증 완료' 체크 시 노션 전송
            if obj.is_verified:
                status_code = send_to_notion(obj)

                # 상태 코드에 따라 커스텀 에러 던지기
                if status_code == 200:
                    self.message_user(request, f"✅ '{obj.title}' 항목이 노션에 등록되었습니다.")
                    logger.info(f"[NOTION SUCCESS] ID: {obj.id} 전송 완료")
                else:
                    # 에러 상황이면 직접 던지지 않고 NotionAPIError를 발생시킴
                    error_msg = f"노션 전송 실패 (상태 코드: {status_code})"
                    if status_code == 401: error_msg = "노션 인증 실패 (토큰 확인 필요)"
                    if status_code == 404: error_msg = "노션 데이터베이스 ID 오류"

                    raise NotionAPIError(error_msg)

        except (NotionAPIError, EmptyAiAnswerError) as e:
            # [중요] 우리가 만든 예외 클래스를 활용한 로깅
            logger.warning(f"[{e.__class__.__name__}] {e.message} (User: {request.user})")

            # 어드민 상단에 에러 메시지 노출
            self.message_user(request, f"❌ 오류: {e.message}", level='error')

            # (옵션) 에러 발생 시 '검증 완료'를 다시 해제하고 저장하고 싶다면 아래 주석 해제
            # obj.is_verified = False
            # super().save_model(request, obj, form, change)

        except Exception as e:
            # 예상치 못한 시스템 에러 (500번대 상황)
            logger.error(f"[SYSTEM ERROR] {str(e)}", exc_info=True)
            self.message_user(request, "시스템 오류가 발생했습니다. 로그를 확인하세요.", level='error')