🤖 AI 학습 조교 아카이빙 시스템
디스코드 질문 수집부터 AI 답변 생성, 그리고 노션 아카이빙까지 한 번에 관리하는 통합 학습 보조 시스템입니다.

1. 프로젝트 개요
수강생이 디스코드에서 질문을 던지면, Google Gemini 2.5 Flash 모델이 즉시 답변을 제공하고, 관리자(조교)가 장고 어드민에서 내용을 검수 및 수정한 뒤 버튼 하나로 노션 데이터베이스에 학습 로그를 저장합니다.

2. 주요 기능
Discord Bot: 실시간 질문 감지 및 AI 자동 답변 응답.

Gemini AI 연동: 최신 LLM을 활용한 코드 분석 및 문제 해결 전략 제공.

Django Admin: 수집된 질문과 AI 답변을 관리자가 직접 수정하고 승인하는 대시보드.

Notion API 연동: 승인된 질문-답변 쌍을 노션 데이터베이스로 자동 전송 및 아카이빙.

Image Analysis: 질문에 포함된 스크린샷(에러 로그 등)을 분석하여 답변에 반영.

3. 시스템 아키텍처
질문 수집: 수강생이 디스코드에 질문 게시.

AI 분석: 봇이 질문(텍스트+이미지)을 Gemini AI에게 전달하여 핵심 요약 답변 생성.

데이터 저장: 질문과 AI 답변이 로컬 SQLite DB(Django)에 임시 저장.

검수 및 전송: 관리자가 어드민에서 내용을 확인/수정한 뒤 '검증 완료' 시 노션으로 전송.

4. 기술 스택
Language: Python 3.x

Framework: Django (Admin)

AI: Google Generative AI (Gemini 2.5 Flash)

API: Discord API (discord.py), Notion API

Environment: Windows/Mac (Cross-platform)

5. 설치 및 설정 (Getting Started)
환경 변수 설정 (.env)
프로젝트 루트에 .env 파일을 생성하고 아래 정보를 입력해야 합니다.

코드 스니펫

GOOGLE_API_KEY=your_gemini_api_key
DISCORD_BOT_TOKEN=your_discord_bot_token
NOTION_TOKEN=your_notion_internal_integration_token
NOTION_DB_ID=your_notion_database_id
실행 방법
가상환경 생성 및 활성화

Bash

python -m venv venv
source venv/bin/activate  # Mac
# venv\Scripts\activate  # Windows
라이브러리 설치

Bash

uv init
uv sync
데이터베이스 마이그레이션 및 서버 실행

Bash

python manage.py migrate
python manage.py runserver
6. 업데이트 노트 (최근 개선 사항)
답변 최적화: 프롬프트 엔지니어링을 통해 핵심 위주의 간결한 답변 생성(Temperature 조절).

에러 핸들링: 노션 API 글자 수 제한(2,000자) 및 특수 문자 세척 기능 추가.

로깅 시스템: 전송 실패 시 상세 에러 원인(Property 일치 여부 등)을 터미널에 출력하도록 개선.

🚀 [2025-12-28] 에러 핸들링 및 로깅 시스템 고도화
단순히 코드가 실행되는 것을 넘어, 관리자가 조교 업무를 모니터링하고 예외 상황을 즉시 파악할 수 있도록 시스템을 강화했습니다.

1. 커스텀 예외 처리 (Custom Exception Handling)
EmptyAiAnswerError: AI 답변 필드가 비어 있는 상태에서 '검증 완료'를 시도할 경우 발생하는 예외를 추가했습니다.

NotionAPIError: 노션 API 전송 중 발생하는 통신 오류를 세분화하여 관리합니다.

2. 로깅 시스템 (Logging System)
로그 파일 자동 생성: Logs/django.log 파일에 모든 시스템 활동을 기록합니다.

레벨별 로깅 적용:

[INFO]: 노션 전송 성공 및 정상 데이터 처리.

[WARNING]: 필수 데이터 누락 등 운영상 주의가 필요한 상황.

[ERROR]: 시스템 장애 및 API 통신 실패 상세 내역.

터미널 실시간 모니터링: 개발 및 운영 중 터미널(Console)을 통해 실시간으로 조교 활동을 확인할 수 있습니다.

🛠️ 기술적 변경 사항

Settings: LOGGING 설정을 통해 console 및 file 핸들러 이중화.

Middleware: 예외 발생 시 JSON 응답 또는 로깅을 처리하는 미들웨어 구조 설계.


