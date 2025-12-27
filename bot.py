import discord
from discord.ext import commands
import os
import django
from dotenv import load_dotenv
from asgiref.sync import sync_to_async  # 비동기 DB 저장을 위해 필수!

# 1. 환경 변수 및 장고 설정 로드
load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # 프로젝트명 확인!
django.setup()

# 장고 모델과 서비스 임포트
from archiver.models import QnALog
from archiver.services import analyze_qna

# 2. 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'✅ 봇 로그인 성공: {bot.user.name}')


@bot.event
async def on_message(message):
    # 봇 본인의 메시지는 무시
    if message.author == bot.user:
        return

    # '!분석'으로 시작하는 메시지 처리
    if message.content.startswith('!분석'):
        print(f"--- 분석 요청 감지 ({message.author}) ---")

        question_text = message.content.replace('!분석', '').strip()

        # 이미지 처리 (첨부파일이 있는 경우)
        image_path = None
        if message.attachments:
            attachment = message.attachments[0]
            if any(attachment.filename.lower().endswith(ext) for ext in ['png', 'jpg', 'jpeg']):
                if not os.path.exists('media/qna_images'):
                    os.makedirs('media/qna_images')
                image_path = f"media/qna_images/{attachment.filename}"
                await attachment.save(image_path)

        # 사용자에게 대기 메시지 전송
        status_msg = await message.channel.send("🤖 Gemini AI가 분석 중입니다... 잠시만 기다려주세요.")

        try:
            # 1. Gemini AI 분석 호출 (services.py 실행)
            ai_result = analyze_qna(question_text, image_path)

            # 2. 장고 DB에 질문/답변 기록 저장 (비동기 처리)
            # 수강생들의 질문을 문서화하기 위한 핵심 로직입니다.
            await sync_to_async(QnALog.objects.create)(
                title=f"Discord Q&A ({message.author.name})",
                question_text=question_text,
                ai_answer=ai_result,
            )

            # 3. 디스코드 전송용 글자 수 처리 (2,000자 제한 방지)
            display_result = ai_result
            if len(ai_result) > 1900:
                display_result = ai_result[:1900] + "\n\n...(내용이 너무 길어 일부 생략되었습니다. 전체 내용은 관리자 페이지에서 확인하세요.)"

            await message.reply(f"📝 **분석 결과:**\n\n{display_result}")

        except Exception as e:
            # 에러 발생 시 사용자에게 알림 (할당량 초과 등)
            error_msg = str(e)[:1500]
            await message.reply(f"❌ 에러 발생: {error_msg}\n(API 할당량 초과 시 약 1분 후 다시 시도해 주세요.)")

        finally:
            # "분석 중" 메시지 삭제
            try:
                await status_msg.delete()
            except:
                pass

    # 다른 커맨드 처리 허용
    await bot.process_commands(message)


# 3. 봇 실행
bot.run(os.getenv('DISCORD_BOT_TOKEN'))