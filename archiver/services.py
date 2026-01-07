from http.client import responses
import requests
import logging
import re
import google.generativeai as genai
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
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"▶ API KEY 로드됨?: {'YES' if api_key else 'NO'}")

    genai.configure(api_key=api_key)

    # 먼저 최근 질문들을 모두 조회 (검증 여부 관계없이)
    past_questions = QnALog.objects.all().order_by('-created_at')[:30]
    print(f"▶ 전체 질문 수: {past_questions.count()}")

    verified_questions = [q for q in past_questions if q.is_verified]
    print(f"▶ 그 중 is_verified=True: {len(verified_questions)}개")
    print(f"▶ 그 중 notion_url 있음: {len([q for q in verified_questions if q.notion_page_url])}개")

    if not past_questions.exists():
        print("❌ DB에 질문 자체가 없음 → None 반환")
        return None
    print("▶ 비교 대상 질문 목록:")

    # 각 질문과 순차적으로 비교
    for q in past_questions:
        try:
            print(f"  비교 중: ID {q.id} - {q.question_text[:50]}...")

            # 질문 전체를 비교 (더 정확한 유사도 판정)
            q1_text = q.question_text[:500] if len(q.question_text) > 500 else q.question_text
            q2_text = new_question[:500] if len(new_question) > 500 else new_question

            prompt = f"""Are these two questions asking about the same thing?

Question 1: {q1_text}

Question 2: {q2_text}

Answer with only YES or NO:"""

            model = genai.GenerativeModel('gemini-2.5-flash')

            # 안전 설정 완화
            safety_settings = {
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=5,
                    temperature=0,
                ),
                safety_settings=safety_settings
            )

            # response가 유효한지 확인
            if not response.candidates or not response.candidates[0].content.parts:
                print(f"    → 응답 없음 (finish_reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'})")
                continue

            result = response.text.strip().upper()
            print(f"    → 응답: {result}")

            if "YES" in result:
                print(f"✅ 중복 발견! ID {q.id} 반환")
                return q

        except Exception as e:
            print(f"    → 에러: {str(e)[:100]}")
            continue

    print("✅ 모든 비교 완료 - 신규 질문")
    return None



def analyze_qna(question_text, image_path=None):
    """신규 질문에 대해 설정하신 조교 답변 생성"""
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    # 프롬프트
    prompt = f"""
    너는 불필요한 설명을 하지 않는 실력파 개발 조교야.
    인사말은 생략하고 다음 구조로 핵심만 짧게 답해줘.

    [출력 양식]
    제목: (질문의 핵심 의도를 한 문장으로 요약)
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
    content = [prompt]

    # 이미지가 있는 경우 PIL로 로드
    if image_path and os.path.exists(image_path):
        try:
            img = Image.open(image_path)
            content.insert(0, img)  # 이미지를 먼저 추가
        except Exception as e:
            print(f"이미지 로딩 에러 {e}")

    for attempt in range(3):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')

            # 안전 설정 완화
            safety_settings = {
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }

            response = model.generate_content(
                content,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=4096,
                ),
                safety_settings=safety_settings
            )

            # response가 유효한지 확인
            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning(f"⚠️ Gemini 응답 없음 (analyze_qna). finish_reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")
                return None

            return response.text
        except Exception as e:
            error_msg = str(e)
            # Rate limit 에러 처리
            if "quota" in error_msg.lower() or "rate" in error_msg.lower():
                if attempt < 2:
                    time.sleep(7)
                    continue
                else:
                    return None
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
    
    # 키워드 추출
    keywords = extract_keywords(obj.question_text, obj.ai_answer)

    properties = {
        "이름": {"title": [{"text": {"content": (obj.title or "질문")[:100]}}]},
        "질문내용": {"rich_text": [{"text": {"content": (obj.question_text or "내용 없음")[:1990]}}]},
        "AI답변": {"rich_text": [{"text": {"content": (obj.ai_answer or "답변 대기 중")[:1990]}}]},
        "카테고리": {"select": {"name": obj.category or "General"}},
        "질문횟수": {"number": int(obj.hit_count)}
    }

    # 키워드가 있으면 추가
    if keywords:
        properties["키워드"] = {
            "multi_select": [{"name": keyword[:50]} for keyword in keywords]
        }

    data = {
        "parent": {"database_id": database_id},
        "properties": properties
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

    # #뒤에 붙은 태그 먼저 찾습니다
    tags = re.findall(r"#(\w+)", ai_text)
    for tag in tags:
        for cat in NOTION_CATEGORIES:
            if tag.lower() == cat.lower():
                return cat

    # 태그가 없으면 기존 방식대로 본문 검색
    for cat in NOTION_CATEGORIES:
        if cat.lower() in ai_text.lower():
            return cat

    
    # 그래도 없으면 정규표현식으로 단어 추출
    match = re.search(r"(\w+)", ai_text)
    if match:
        extracted = match.group(1)
        # 추출된 단어가 카테고리 리스트에있는지 확인
        for cat in NOTION_CATEGORIES:
            if cat.lower() == extracted.lower():
                return cat
    return "General"

def extract_keywords(question_text, ai_answer):
    if not question_text and not ai_answer:
        return []

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return []

    genai.configure(api_key=api_key)

    prompt = f"""
    아래 질문과 답변을 분석해서 핵심 키워드 3~5개를 추출해줘.

    [규칙]
    - 기술용어, 라이브러리명, 개념명 등 핵심 키워드만 추출
    - 각 키워드는 쉼표로 구분해서 한줄로 출력
    - 예시: Django, ORM, 쿼리셋, 모델, 마이그레이션
    - 키워드 3~5개만 추출
    - 불필요한 설명 없이 키워드만 출력

    [질문]
    {question_text[:500]}

    [답변]
    {ai_answer[:1000] if ai_answer else ""}
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')

        # 안전 설정 완화
        safety_settings = {
            genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
            genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
        }

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=200,
            ),
            safety_settings=safety_settings
        )

        # response가 유효한지 확인
        if not response.candidates or not response.candidates[0].content.parts:
            logger.warning(f"⚠️ Gemini 응답 없음 (extract_keywords). finish_reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")
            return []

        result = response.text.strip()
        keywords = [kw.strip() for kw in result.split(",") if kw.strip()]
        return keywords[:5]
    except Exception as e:
        logger.exception(f"키워드 추출 에러: {e}")
        return []