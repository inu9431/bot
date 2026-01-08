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
    # 질문 빈도(hit_count)를 가장 앞에 나오게 함
    list_display = ('id', 'hit_count', 'title','is_verified', 'category', 'created_at')
    list_display_links = ('id', 'title',)
    # 2. 리스트에서 바로 수정
    # 상세 페이지에 들어가지 않고 체크박스 하나로 노션 전송을 결정
    list_editable = ('is_verified', 'category')

    # 필터 및 검색
    list_filter = ('is_verified', 'category', 'created_at')
    search_fields = ('title','question_text', 'ai_answer')

    # 정렬 질문횟수가 많은 순서대로
    ordering = ('-created_at', '-hit_count')


    # 저장 로직
    def save_model(self, request, obj, form, change):
        """
        저장 버튼을 누른 떄 실행되는 로직
        """
        print(f"DEBUG: 저장 시작: {obj.id}, title:{obj.title}")
        try:
            # 검증 완료가 체크되어있고, 아직 노션 링크가 없을떄만 전송
            # 이미 있다면 중복 전송 방지
            super().save_model(request, obj, form, change)
            self.message_user(request, f"DEBUG: {obj.id}번 데이터가 DB에 저장되었습니다.")
            print("DEBUG: 저장 완료 메시지 호출됨")
            
            if obj.is_verified and not obj.notion_page_url:

                if not obj.ai_answer:
                    self.message_user(request, " 저장은 완료되었으나 AI답변이 비어있어서 전송은 안되었습니다", level='warning')
                    return

                status_code = send_to_notion(obj)

                if status_code == 200:
                    # 전송 성공시 URL 업데이트를 위한 한번 더 저장
                    obj.save(update_fields=['notion_page_url'])
                    self.message_user(request, f"✅ '{obj.title}' 항목이 노션 FAQ에 등록되었습니다.")
                    logger.info(f"[NOTION SUCCESS] ID: {obj.id} 전송 완료")
                else:
                    # 상세 에러메세지
                    error_msg = f"노션 전송 실패 (상태 코드: {status_code})"
                    if status_code ==401: error_msg = "노션 인증 실패 (토큰을 확인하세요)"
                    if status_code ==404: error_msg = "노션 데이터베이스 ID를 찾을 수 없습니다"
                    raise NotionAPIError(error_msg)
        
            
        except NotionAPIError as e:
            # 커스텀 에러 로깅 및 사용자 알림
            logger.warning(f"[NotionAPIError]{str(e)}")
            self.message_user(request, f"❌ DB 저장은 되었으나 연동 실패: {str(e)}", level='error')

        except Exception as e:
            # 예상치 못한 시스템 에러
            logger.error(f"[SYSTEM ERROR] {str(e)}", exc_info=True)
            self.message_user(request, f"❌ 오류 발생: {str(e)}", level='error')
    # 상세 화면 레이아웃 최적화
    fieldsets = (
        ('기본 정보', {
            'fields': ('category', 'title', 'hit_count')
        }),
        ('질문 및 답변', {
            'fields': ('question_text', 'image', 'ai_answer')
        }),
        ('검증 및 연동', {
            'fields': ('is_verified', 'notion_page_url')
        }),
    )
    readonly_fields = ('notion_page_url', 'hit_count')


