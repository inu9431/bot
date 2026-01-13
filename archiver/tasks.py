import os
import logging
import requests
from .services import QnAService

logger = logging.getLogger(__name__)

def task_process_question(question_text: str, image_path: str = None):
    service = QnAService()
    
    if image_path and not os.path.exists(image_path):
        logger.warning(f"태스크 시작 전 이미지 파일이 존재하지 않음: {image_path}")

    try:
        # 1. AI 분석 및 DB 저장
        obj, is_duplicated = service.process_question_flow(question_text, image_path)

        # 2. 웹훅 발송
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if webhook_url:
            payload = {
                # 괄호와 문구를 정리했습니다.
                "content": f"✅ **AI 분석 완료 (ID: {obj.id})**\n\n{obj.ai_answer}\n\n*관리자 검증 대기 중입니다. 어드민에서 확인해주세요.*"
            }
            # 실제 발송
            res = requests.post(webhook_url, json=payload)
            logger.info(f"디코드 웹훅 발송 결과 코드: {res.status_code}")

        logger.info(f" QnA 처리완료: ID{obj.id} (중복여부: {is_duplicated})")
        return f" 처리 완료 ID {obj.id} (중복: {is_duplicated})"
        
    except Exception as e:
        logger.error(f" 비동기 태스크 실패: {str(e)}", exc_info=True)
        raise e