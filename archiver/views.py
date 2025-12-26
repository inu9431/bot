from django.shortcuts import render
from .models import QnALog
from .services import analyze_qna

def upload_qna(request):
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        image = request.FILES.get('image')

        # 우선 임시 저장(이미지 경로 확보)
        log = QnALog.objects.create(question_text=question_text, image=image)

        #  AI 분석 실행
        image_path = log.image.path if log.image else None
        ai_result = analyze_qna(question_text, image_path)

        # AI 결과 업데이트
        log.ai_answer = ai_result
        log.title = f"Q&A - {log.id}번 사례"
        log.save()

        return render(request, 'archiver/upload_qna.html', {'log': log})

    return render(request, 'archiver/upload_qna.html')

def index(request):
    logs = QnALog.objects.all().order_by('-created_at')
    return render(request, 'archiver/index.html', {'logs': logs})