from django.db import models

class QnALog(models.Model):
    category = models.CharField(max_length=50, default='General')
    title = models.CharField(max_length=200) # AI가 요약한 제목
    question_text = models.TextField() # 학생 질문
    image = models.ImageField(upload_to='qna_images/', null=True, blank=True)
    ai_answer = models.TextField() # AI가 정리한 답변

    is_verified = models.BooleanField(default=False, verbose_name="검증 완료")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

