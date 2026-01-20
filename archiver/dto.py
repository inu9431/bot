from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime




class QnACreateDTO(BaseModel):
    """AI 분석 결과를 바탕으로 QnA 생성을 요청할떄 사용하는 데이터 전송 객체"""

    question_text: str
    title: str
    summary: Optional[str] = None
    reason: Optional[str] = None
    solution_code: Optional[str] = None
    checkpoint: Optional[str] = None
    category: Optional[str] = "General"
    keywords: List[str] = Field(default_factory=list)
    image_path: Optional[str] = None
    ai_answer: Optional[str] = None
    hit_count: Optional[int] = 1

    class Config:
        frozen = True # 객체 생성 후 수정불가
        from_attributes = True


class QnAResponseDTO(BaseModel):
        id: int
        question_text: str
        title: str
        summary: Optional[str] = None
        reason: Optional[str] = None
        solution_code: Optional[str] = None
        checkpoint: Optional[str] = None
        category: Optional[str] = None
        keywords: Optional[List[str]] = None
        image_path: Optional[str] = None
        ai_answer: Optional[str] = None
        hit_count: Optional[int] = 1
        created_at: Optional[datetime] = None

        class Config:
            frozen = True
            from_attributes = True # Django에서 모든 모델 같은 객체에서 바로 DTO룰 생성할수 있게 해주는 설정

