🤖 AI 학습 조교 아카이빙 시스템 (v2.0)
디스코드 질문 수집부터 AI 답변 생성, 중복 질문 탐지, 그리고 노션 아카이빙까지 한 번에 관리하는 통합 학습 보조 시스템입니다.

📝 프로젝트 개요
수강생이 디스코드에서 질문을 던지면, Google Gemini 1.5 Flash 모델이 즉시 답변을 제공합니다. 특히 유사 질문 탐지 엔진을 통해 이미 검증된 정답이 있을 경우 노션 링크를 즉시 안내하여 조교의 업무 효율을 극대화합니다.

🌟 주요 기능 (Update)
Discord Bot (!질문): 실시간 질문 감지 및 AI 자동 답변. (기존 !분석에서 변경)

지능형 유사도 판정 (Similarity Check): AI가 새 질문과 기존 DB를 비교하여 중복 여부를 판정.

질문 빈도(Hit Count) 집계: 중복 질문 발생 시 새 레코드를 만들지 않고 기존 질문의 '질문 빈도'를 자동으로 카운팅.

노션 URL 즉시 제공: 이미 검증 완료된 질문은 분석 과정을 생략하고 노션 상세 페이지 URL을 즉시 응답.

Image Analysis: 질문에 포함된 스크린샷(에러 로그 등)을 분석하여 답변에 반영.

Django Admin: 수집된 질문과 AI 답변을 관리자가 직접 수정하고 승인하는 대시보드.

Notion API 연동: 승인된 질문-답변 쌍을 노션 데이터베이스로 자동 전송 및 아카이빙.

🛠️ 시스템 아키텍처 (Workflow)
질문 수집: 수강생이 디스코드에 !질문과 함께 내용 게시.

유사도 검사: AI가 기존 DB(특히 is_verified=True 항목)와 대조.

데이터가 있는 경우 (중복): hit_count 증가 → (검증 시) 해당 노션 URL 즉시 답변 → 종료.

데이터가 없는 경우 (신규): Gemini AI 분석 → 조교 답변 출력 → DB 임시 저장.

검수 및 전송: 관리자가 어드민에서 내용을 확인/수정한 뒤 '검증 완료' 시 노션으로 전송.

💻 기술 스택
Language: Python 3.13+

Framework: Django 5.x (Admin, ORM)

AI: Google Gemini 1.5 Flash

API: Discord API (discord.py), Notion API

Utility: re (Regex for ID extraction), asgiref (Sync-to-Async)

⚙️ 설정 및 실행
1. 환경 변수 설정 (.env)
코드 스니펫

GEMINI_API_KEY=your_gemini_api_key
DISCORD_BOT_TOKEN=your_discord_bot_token
NOTION_TOKEN=your_notion_token
NOTION_DB_ID=your_notion_db_id
NOTION_BOARD_URL=https://www.notion.so/your_board_link # 전체 게시판 주소
2. 실행 방법
Bash

# 가상환경 및 패키지 설치 (uv 권장)
uv sync

# DB 마이그레이션 및 봇 실행
python manage.py migrate
python bot.py
🚀 업데이트 노트 (2026-01-02)
1. 명령어 체계 최적화
사용자 접근성을 높이기 위해 명령어 접두사를 !질문으로 통일했습니다.

2. 중복 질문 판정 로직 고도화
**정규표현식(Regex)**을 도입하여 AI 답변에서 숫자 ID를 추출하는 안정성을 확보했습니다.

프롬프트 엔지니어링을 통해 단순 문장 비교가 아닌 **'질문의 의도'**를 분석하도록 개선했습니다.

3. Hit Count 기반 데이터 관리
동일한 질문이 반복될 경우 노션에 중복 페이지가 생성되지 않도록 로직을 수정했습니다.

질문 빈도 통계를 통해 어떤 개념이 학생들에게 어려운지 데이터로 확인할 수 있습니다.

4. 에러 핸들링 강화
글자 수 제한(2,000자): 디스코드와 노션 API의 제약 사항을 준수하도록 출력 전 자동 슬라이싱 기능을 추가했습니다.

실시간 로깅: 터미널에서 AI의 유사도 판정 결과(ID 또는 NEW)를 실시간 모니터링할 수 있습니다.

🚀 업데이트 노트 (2026-01-08)

검색 엔진 성능 최적화 (New)

PostgreSQL의 pg_trgm 확장을 도입하여 DB 레벨에서 유사 질문을 고속 탐색합니다.

GIN 인덱스 적용으로 데이터가 쌓여도 응답 속도가 일정하게 유지됩니다.

토큰 절약 및 비용 효율화

모든 FAQ를 LLM에 전송하던 방식에서, 관련 있는 상위 질문들만 전달하는 방식으로 변경하여 API 호출 비용을 획기적으로 낮췄습니다.

운영 편의성 강화 (Admin UI)

Django Admin 내 save_model 커스터마이징을 통해 "수정은 자유롭게, 전송은 승인 시에만" 이루어지도록 로직을 분리했습니다.


AI 답변이 없는 상태에서 전송을 시도할 경우 경고 메시지를 띄워 데이터 누락을 방지합니다.

📅 업데이트 내용 (2026-01-09)
1. 로컬 개발 환경 도커라이징 (Dockerization)
Docker 도입: 맥북/윈도우 등 OS 환경에 구애받지 않는 일관된 개발 환경 구축.

Multi-Container 설정: docker-compose를 사용하여 Django(web)와 PostgreSQL(db)을 독립된 컨테이너로 관리.

볼륨 마운트(Volumes): 로컬 코드 수정 사항이 도커 컨테이너에 실시간 반영되도록 설정하여 개발 편의성 증대.

2. 디스코드 봇 - 장고 서버 연동 최적화
컨테이너 간 통신 설정: 디스코드 봇이 도커 네트워크 내부 주소(http://web:8000)를 통해 장고 API와 통신하도록 아키텍처 개선.

보안 설정 업데이트: ALLOWED_HOSTS에 내부 컨테이너 호스트(web)를 추가하여 안정적인 데이터 송수신 확보.

3. 테스트 및 운영 자동화
유사 질문 판별 로직: 수강생의 질문이 들어오면 DB 내 유사도를 체크하여 verified(검토완료), duplicate(검토중), new(신규) 상태별로 차등 답변 기능 구현.

노션 링크 반환: 검토가 완료된 질문에 대해 자동으로 노션 페이지 주소를 반환하는 로직 테스트 완료.

Pytest 설정: 테스트 자동화를 위한 pytest.ini 환경 설정 추가.

🛠 실행 방법 (윈도우/맥 공통)
환경 변수 설정: .env 파일에 DISCORD_BOT_TOKEN, GEMINI_API_KEY, NOTION_TOKEN 등 설정.

컨테이너 빌드 및 실행:

Bash

docker-compose up --build -d
디스코드 봇 실행:
## 
Bash

docker-compose exec web python run_bot.py
