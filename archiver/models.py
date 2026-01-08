from django.db import models
from django.contrib.postgres.indexes import GinIndex

class QnALog(models.Model):
    CATEGORY_CHOICES = [
        ("Git", "Git"),
        ("Linux", "Linux"),
        ("DB", "DB"),
        ("Python", "Python"),
        ("Flask", "Flask"),
        ("Django", "Django"),
        ("FastAPI", "FastAPI"),
        ("General", "General"),
    ]

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='General',
        verbose_name="카테고리")

    title = models.CharField(max_length=200) # AI가 요약한 제목
    question_text = models.TextField() # 학생 질문
    image = models.ImageField(upload_to='qna_images/', null=True, blank=True)
    ai_answer = models.TextField() # AI가 정리한 답변

    is_verified = models.BooleanField(default=False, verbose_name="검증 완료")
    hit_count = models.PositiveIntegerField(default=1, verbose_name="질문 빈도")
    parent_question = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_questions',
        verbose_name="상위 질문")

    notion_page_url = models.URLField(max_length=500, null=True, blank=True, verbose_name="노션 페이지 링크")
    keywords = models.JSONField(default=list, blank=True, null=True, verbose_name="세부 키워드")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "Q&A Log"
        verbose_name_plural = "Q&A 로그 목록"
        ordering = ["-created_at"]

        indexes = [
            GinIndex(
                fields =['question_text'],
                name='qna_question_tgrm_idx',
                opclasses=['gin_grgm_ops']
            ),
        ]

    def __str__(self):
        return f"[{self.category}] {self.title}] (빈도: {self.hit_count})"

