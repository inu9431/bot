# 파이썬 환경 설정
FROM python:3.10-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# 필수 OS 패키지 설치 (psql 연결용)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# 디렉토리 작업 설정
WORKDIR /app

# 라이브러리 설치
COPY pyproject.toml uv.lock ./
RUN  uv sync --frozen --no-install-project

# 소스 코드 복사
COPY . .

# 프로젝트 설치 
RUN uv sync --frozen

# PATH 가상환경 추가
ENV PATH="/app/.venv/bin:$PATH"

# 실행 명령
# venv를 따로 활성화 할 필용벗이 'uv run'을 사용하면 알아서 실행됨
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
