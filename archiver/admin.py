from django.contrib import admin
from import_export.admin import ExportActionMixin
from .models import QnALog
from .services import send_to_notion  # 아까 작성한 노션 전송 함수 가져오기


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
        """
        관리자 페이지에서 저장(Save) 버튼을 누를 때 호출됩니다.
        '검증 완료'가 체크된 데이터만 노션으로 전송합니다.
        """
        # 먼저 DB에 변경 사항(수정된 답변, 체크 여부 등)을 저장
        super().save_model(request, obj, form, change)

        # '검증 완료'가 체크되어 있는 경우에만 노션 API 호출
        if obj.is_verified:
            status_code = send_to_notion(obj)

            if status_code == 200:
                self.message_user(request, f"✅ '{obj.title}' 항목이 노션 FAQ에 등록되었습니다.")
            elif status_code == 401:
                self.message_user(request, "❌ 노션 인증 실패: 토큰이나 페이지 연결을 확인하세요.", level='error')
            elif status_code == 404:
                self.message_user(request, "❌ 노션 데이터베이스를 찾을 수 없습니다: ID를 확인하세요.", level='error')
            else:
                self.message_user(request, f"❌ 노션 전송 중 오류 발생 (상태 코드: {status_code})", level='error')