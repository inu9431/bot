from .services import QnAService
import logging

logger = logging.getLogger(__name__)

def task_process_question(qeustion_text: str, image_path: str = None):
"""
Django-Q 워커가 백그라운드에서 실행하는 태스크
"""
    service = QnAService()
    try:
        # 유사도 체크 -> Gemini 호출 -> DB 저장
        obj, is_duplicated = service.process_question_flow(qeustion_text, image_path)
        return f" 처리 완료 ID {obj.id} (중복: {is_duplicated})"
    except Exception as e:
        logger.error(f" 비동기 태스크 실패: {str(e)}")
        raise e
