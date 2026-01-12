import logging

from django.contrib import admin
from import_export.admin import ExportActionMixin

from common.exceptions import NotionAPIError

from .models import QnALog
from .services import QnAService

logger = logging.getLogger("apps")


@admin.register(QnALog)
class QnALogAdmin(ExportActionMixin, admin.ModelAdmin):
    # 1. 목록 화면 설정
    # 질문 빈도(hit_count)를 가장 앞에 나오게 함
    list_display = ("id", "hit_count", "title", "is_verified", "category", "created_at")
    list_display_links = (
        "id",
        "title",
    )
    # 2. 리스트에서 바로 수정
    # 상세 페이지에 들어가지 않고 체크박스 하나로 노션 전송을 결정
    list_editable = ("is_verified", "category")

    # 필터 및 검색
    list_filter = ("is_verified", "category", "created_at")
    search_fields = ("title", "question_text", "ai_answer")

    # 정렬 질문횟수가 많은 순서대로
    ordering = ("-created_at", "-hit_count")

    # 저장 로직
    def save_model(self, request, obj, form, change):
        """
        저장 버튼을 누른 떄 실행되는 로직
        """
        # 검증 완료가 체크되어있고, 아직 노션 링크가 없을떄만 전송
        # 이미 있다면 중복 전송 방지
        super().save_model(request, obj, form, change)

        # 검증완료 체크 & 아직 노션 링크가 없을떄만 전송
        if obj.is_verified and not obj.notion_page_url:
            if not obj.ai_answer:
                self.message_user(
                    request,
                    " 저장은 완료되었으나 AI답변이 비어있어서 전송은 안되었습니다",
                    level="warning",
                )
                return
            try:
                service = QnAService()
                service.publish_to_notion(obj.id)

                self.message_user(request, f" [notion_success] : {obj.id} 전송 완료")

            except NotionAPIError as e:
                logger.warning(f" [NotionAPIError] {str(e)}")
                self.message_user(request, f" 노션 연동 실패 {str(e)}", level="error")
            except Exception as e:
                logger.error(f" [System Error] {str(e)}", exc_info=True)
                self.message_user(request, f" 시스템 오류 발생 {str(e)}", level="error")

    fieldsets = (
        ("기본 정보", {"fields": ("category", "title", "hit_count")}),
        ("질문 및 답변", {"fields": ("question_text", "ai_answer")}),
        ("검증 및 연동", {"fields": ("is_verified", "notion_page_url")}),
    )
    readonly_fields = ("notion_page_url", "hit_count")
