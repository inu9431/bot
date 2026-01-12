import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class QnADTO:
    """AI 분석 결과 및 질문 정보를 담는 데이터 전송 객체"""

    question_text: str
    title: str
    summary: Optional[str] = None
    reason: Optional[str] = None
    solution_code: Optional[str] = None
    checkpoint: Optional[str] = None
    category: Optional[str] = "General"
    keywords: List[str] = field(default_factory=list)
    image_path: Optional[str] = None
    ai_answer: Optional[str] = None
    hit_count: Optional[int] = 1

    @classmethod
    def from_ai_response(
        cls,
        question_text: str,
        ai_raw_text: str,
        category: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        image_path: Optional[str] = None,
    ) -> "QnADTO":
        """간단 파싱: ai_raw_text에서 '제목:' 라인을 찾아 제목을 추출하고, 나머지는 summary로 보관"""
        title_match = re.search(r"제목:\s*(.*)", ai_raw_text)
        title = title_match.group(1).strip() if title_match else "신규 질문"

        # summary는 첫 200자 정도 추출
        summary = ai_raw_text.strip()[:200] if ai_raw_text else None
        return cls(
            question_text=question_text,
            title=title,
            summary=summary,
            reason=None,
            solution_code=None,
            checkpoint=None,
            category=category or "General",
            keywords=keywords or [],
            image_path=image_path,
            ai_answer=ai_raw_text,
            hit_count=1,
        )
