import google.generativeai as genai
import os
import time
import requests
import json  # 에러 로그 출력을 위해 추가
from PIL import Image
from google.api_core import exceptions
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


def analyze_qna(question_text, image_path=None):
    api_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)

    # 1. 모델명 수정: gemini-2.5-flash는 현재 존재하지 않으므로 가장 최신인 gemini-1.5-flash 사용
    model = genai.GenerativeModel('models/gemini-2.5-flash')

    prompt = f"""
    너는 불필요한 설명을 하지 않는 실력파 개발 조교야.
    인사말은 생략하고 다음 구조로 핵심만 짧게 답해줘.

    [출력 양식]
    1. **문제 요약**: (에러 정체 1문장)
    2. **핵심 원인**: (이유 1~2개 불렛 포인트)
    3. **해결 코드**: (중요 코드 블록. 설명은 주석으로)
    4. **체크포인트**: (실수 방지 팁 하나)

    마지막에 질문 성격에 맞는 태그를 반드시 달아줘 (예: #DB, #Python).

    질문 내용: {question_text}
    """

    content = [prompt]

    if image_path and os.path.exists(image_path):
        try:
            img = Image.open(image_path)
            content.append(img)
        except Exception as e:
            print(f"이미지 로딩 에러: {e}")

    for attempt in range(3):
        try:
            response = model.generate_content(content)
            return response.text
        except exceptions.ResourceExhausted:
            if attempt < 2:
                time.sleep(10)
                continue
            else:
                return "❌ 현재 사용자가 많아 AI 분석이 지연되고 있습니다."
        except Exception as e:
            return f"❌ 오류 발생: {str(e)}"


def clean_text(text):
    """노션 API 오류를 방지하기 위해 텍스트에서 불필요한 제어 문자를 제거합니다."""
    if text is None:
        return ""
    # 윈도우식 줄바꿈(\r) 제거 및 앞뒤 공백 제거
    return str(text).replace("\r", "").strip()


def send_to_notion(obj):
    """
    장고 관리자 페이지에서 승인된 데이터를 노션으로 전송하고 상세 에러를 출력합니다.
    """
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DB_ID")

    if not notion_token or not database_id:
        print("❌ 에러: NOTION_TOKEN 또는 NOTION_DB_ID가 설정되지 않았습니다.")
        return 400

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # 데이터 세척 및 노션 글자수 제한(2000자) 적용
    title = clean_text(obj.title or "수강생 질문")
    question = clean_text(obj.question_text or "내용 없음")[:2000]
    answer = clean_text(obj.ai_answer or "답변 대기 중")[:2000]
    category = clean_text(obj.category if obj.category else "General")

    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "이름": {
                "title": [{"text": {"content": title}}]
            },
            "질문내용": {
                "rich_text": [{"text": {"content": question}}]
            },
            "AI답변": {
                "rich_text": [{"text": {"content": answer}}]
            },
            "카테고리": {
                "select": {"name": category}
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        # 상세 에러 로그 출력 부분
        if response.status_code != 200:
            print("\n" + "=" * 60)
            print(f"❌ 노션 전송 실패 (상태 코드: {response.status_code})")
            print(f"에러 상세: {response.text}")  # 노션이 보낸 진짜 이유가 여기 찍힙니다.
            print("=" * 60 + "\n")
        else:
            print(f"\n✅ 노션 전송 성공: {title}\n")

        return response.status_code
    except Exception as e:
        print(f"❌ 네트워크 오류: {e}")
        return 500