import logging
import os
import requests
from .adapters import NotionAdapter
from .models import QnALog
from django_q.tasks import async_task
from .dto import QnADTO
logger = logging.getLogger(__name__)


def task_process_question(log_id):
    """
    worker에서 실행되는 비동기 태스크
    """
    try:
        # DB에서 가져오기
        log = QnALog.objects.get(id=log_id)
        # adapter가 이해할수 있는 dto로 변환
        dto = QnADTO(
            title=log.title,
            question_text=log.question_text,
            ai_answer=log.ai_answer,
            category=log.category,
            hit_count=log.hit_count,
            keywords=log.keywords,
        )
        # adapter 호출
        adapter = NotionAdapter()
        notion_url = adapter.create_qna_page(dto)

        # 결과 저장
        if notion_url:
            log.notion_page_url = notion_url
            log.save()
            logger.info(f" [worker] 노션 업로드 완료 (ID: {log.id}")
    except Exception as e:
        logger.error(f" [worker] 노션 업로드 실패 (ID: {log_id} : {str(e)}")
        # 실패시 예외를 다시 던져서 django-q가  실패로그를 남김
        raise e



