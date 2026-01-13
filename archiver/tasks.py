
import os
import logging
import requests
from .services import QnAService

logger = logging.getLogger(__name__)


def task_process_question(qeustion_text: str, image_path: str = None):
    #    Django-Q 워커가 백그라운드에서 실행하는 태스크
    service = QnAService()
    if image_path and not os.path.exists(image_path):
        logger.warning(f"태스크 시작 전 이미지 파일이 존재하지않음: {image_path}")

    try:
        # 유사도 체크 -> Gemini 호출 -> DB 저장
        obj, is_duplicated = service.process_question_flow(qeustion_text, image_path)

        # 웹훅 추가
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if webhook_url:
            payload = {
                "content": f" **AI 분석 완료 (ID: {obj.id}**\n\n{obj.ai_answer}\n\n검증 대기중입니다 어드민에서 확인해주세요)"
            }
            requests.post(webhook_url, json=payload)

        logger.info(f" QnA 처리완료: ID{obj.id} (중복여부: {is_duplicated})")
        return f" 처리 완료 ID {obj.id} (중복: {is_duplicated})"
    except Exception as e:
        logger.error(f" 비동기 태스크 실패: {str(e)}", exc_info=True)
        raise e
