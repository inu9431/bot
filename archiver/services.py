from http.client import responses
import requests
import logging
import re
import anthropic
import os
import time
import json  # 에러 로그 출력을 위해 추가
import base64
from PIL import Image
from certifi import contents
from django.db.models.expressions import result
from dotenv import load_dotenv

from archiver.admin import logger
from archiver.models import QnALog

# .env 파일 로드
load_dotenv()
logger = logging.getLogger(__name__)
NOTION_CATEGORIES = ["Git", "Linux", "DB", "Python", "Flask", "Django", "FastAPI", "General"]

def check_similarity_and_get_answer(new_question):
    print("🔥 check_similarity_and_get_answer CALLED 🔥")
    print("\n================ 유사도 체크 시작 ================")
    print(f"▶ 새 질문: {new_question}")
    """
    1. AI를 통해 기존 DB와 유사도 체크
    2. 중복이면 기존 객체 반환, 신규면 None 반환
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    print(f"▶ API KEY 로드됨?: {'YES' if api_key else 'NO'}")

    client = anthropic.Anthropic(api_key=api_key)

    past_questions = QnALog.objects.filter(is_verified=True).order_by('-created_at')[:50]
    print(f"▶ is_verified=True 질문 수: {past_questions.count()}")

    # 검증된 데이터 없으면 전체에서 조회
    if not past_questions.exists():
        past_questions = QnALog.objects.all().order_by('-created_at')[:30]
        print(f"▶ 전체 질문 수: {past_questions.count()}")

    if not past_questions.exists():
        print("❌ DB에 질문 자체가 없음 → None 반환")
        return None
    print("▶ 비교 대상 질문 목록:")

    context = "\n".join([f"ID {q.id}: {q.question_text}" for q in past_questions])

    prompt = f"""
        너는 질문 유사성을 판단하는 조교야. 아래 [기존 리스트]와 [새 질문]을 비교해줘.

        [판정 기준]
        - 핵심 단어가 일치하고 질문의 의도가 같으면 중복으로 간주한다.
        - 문장 구조가 조금 달라도(예: 평서문과 의문문) 해결책이 같다면 중복이다.
        - 중복이라면 해당 질문의 ID 숫자만 출력한다.
        - 정말로 새로운 주제라면 'NEW'라고 출력한다.
        - 중복이면 반드시 숫자 하나만 출력 (예: 25)
        - NEW면 반드시 NEW만 출력
        - 그 외 텍스트, 설명, 줄바꿈 절대 출력 금지

    [기존 리스트]
    {context}

    [새 질문]
    {new_question}
    """
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        result = response.content[0].text.strip()
        logger.info(result)

        if result.isdigit():
            target_id = int(result)
            return QnALog.objects.filter(id=target_id).first()
        if result.upper().startswith("NEW"):
            return None
        logger.warning(f"⚠️ 예상치 못한 AI 응답: {result}")
        return None
    except Exception as e:
        logger.exception(f" 유사도 체크 에러 {e}")
        return None



def analyze_qna(question_text, image_path=None):
    """신규 질문에 대해 설정하신 조교 답변 생성"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    # 프롬프트
    prompt = f"""
    너는 불필요한 설명을 하지 않는 실력파 개발 조교야.
    인사말은 생략하고 다음 구조로 핵심만 짧게 답해줘.

    [출력 양식]
    1. **문제 요약**: (에러 정체 1문장)
    2. **핵심 원인**: (이유 1~2개 불렛 포인트)
    3. **해결 코드**: (중요 코드 블록. 설명은 주석으로)
    4. **체크포인트**: (실수 방지 팁 하나)

    마지막에 질문 성격에 맞는 태그를 반드시 달아줘 (예: #DB, #Python).
    이 리스트에 없는 단어는 절대 사용하지마.
    카테고리 리스트: {",".join(NOTION_CATEGORIES)}
    
    예시: #Python
    
    질문 내용: {question_text}
    """

    # 메시지 컨텐츠 구성
    content = []

    # 이미지가 있는 경우 base64로 인코딩
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file:
                img_data = base64.standard_b64encode(img_file.read()).decode("utf-8")

            # 이미지 타입 확인
            image_media_type = "image/jpeg"
            if image_path.lower().endswith('.png'):
                image_media_type = "image/png"
            elif image_path.lower().endswith('.gif'):
                image_media_type = "image/gif"
            elif image_path.lower().endswith('.webp'):
                image_media_type = "image/webp"

            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_media_type,
                    "data": img_data,
                }
            })
        except Exception as e:
            print(f"이미지 로딩 에러 {e}")

    # 텍스트 프롬프트 추가
    content.append({
        "type": "text",
        "text": prompt
    })

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": content}
                ]
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            if attempt < 2:
                time.sleep(7)
                continue
            else:
                return None
        except Exception as e:
            print(f"AI 에러 {e}")
            return None

def send_to_notion(obj):
    """노션 전송 및 생성된 페이지 URL을 DB에 저장"""
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DB_ID")

    if not notion_token or not database_id:
        return 400

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "이름": {"title": [{"text": {"content": (obj.title or "질문")[:100]}}]},
            "질문내용": {"rich_text": [{"text": {"content": (obj.question_text or "내용 없음")[:1990]}}]},
            "AI답변": {"rich_text": [{"text": {"content": (obj.ai_answer or "답변 대기 중")[:1990]}}]},
            "카테고리": {"select": {"name": obj.category or "General"}},
            "질문횟수": {"number": int(obj.hit_count)}
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            # 노션이 생성한 페이지 URL 저장
            notion_url = response.json().get("url")
            obj.notion_page_url = notion_url
            obj.save()
            print(f" 노션 URL 저장 완료: {notion_url}")
            return response.status_code
        else:
            error_details = response.json()
            print(f"❌ 노션 API 상세 에러: {json.dumps(error_details, indent=2, ensure_ascii=False)}")
            return error_details.get('message', f"에러 {response.status_code}")

    except Exception as e:
        print(f" 네트워크 오류: {e}")
        return 500


def get_final_answer_with_link(obj):
    """
    AI 답변과 env 게시판 링크 반환
    """
    board_url = os.getenv("NOTION_BOARD_URL")

    return f"{obj.ai_answer}\n\n 노션 페이지 확인하기: \n{board_url}"

def extract_category_answer(ai_text):
    """
    노션에 설정된 카테고리 목록과 비교하여 일치하는 경우만 반환합니다
    """
    if not ai_text:
        return "General"

    for cat in NOTION_CATEGORIES:
        if cat.lower() in ai_text.lower():
            return cat

    match = re.search(r"(\w+)", ai_text)
    if match:
        extracted = match.group(1)
        # 추출된 단어가 카테고리 리스트에있는지 확인
        for cat in NOTION_CATEGORIES:
            if cat.lower() == extracted.lower():
                return cat
    return "General"
