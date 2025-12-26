import google.generativeai as genai
import os
from PIL import Image

def analyze_qna(question_text, image_path=None):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    너는 실력 있는 개발 조교야. 다음 학생의 질문을 분석해서 지식 베이스 문서를 만들어줘.
    질문 내용: {question_text}
    
    [요구사항]
    1. 사진이 있다면 사진 속 에러 코드나 SQL 문법을 정확히 읽어낼 것.
    2. 답변은 '원인'과 '해결 방법'으로 나누어 친절하게 설명할 것.
    3. 반드시 JSON 형식이 아닌, 마크다운(Markdown) 스타일의 텍스트로 응답할 것.
    4. 카테고리는 [Python, Django, FastAPI, SQL, 기타] 중 하나로 정할 것.
    """

    content = [prompt]
    if image_path:
        img = Image.open(image_path)
        content.append(img)

    response = model.generate_content(content)
    return response.text