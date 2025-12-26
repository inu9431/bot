import discord
from discord.ext import commands
import os
import django
from dotenv import load_dotenv

# 1. 환경 변수 및 장고 설정 로드
load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # 프로젝트명이 다르면 수정!
django.setup()

# 장고 모델과 서비스 임포트 (반드시 django.setup() 이후에 해야 함)
from archiver.models import QnALog
from archiver.services import analyze_qna

# 2. 봇 설정
intents = discord.Intents.default()
intents.message_content = True  # 브라우저에서 켠 그 권한!
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'✅ 봇 로그인 성공: {bot.user.name}')


@bot.event
async def on_message(message):
    print(f"--- 메시지 감지 ---")
    print(f"작성자: {message.author}")
    print(f"내용: '{message.content}'")
    if message.author == bot.user:
        return

    # '!분석'으로 시작하는 메시지 처리
    if message.content.startswith('!분석'):
        question_text = message.content.replace('!분석', '').strip()

        image_path = None
        if message.attachments:
            attachment = message.attachments[0]
            if any(attachment.filename.lower().endswith(ext) for ext in ['png', 'jpg', 'jpeg']):
                # media 폴더가 없다면 미리 만들어두세요
                if not os.path.exists('media/qna_images'):
                    os.makedirs('media/qna_images')

                image_path = f"media/qna_images/{attachment.filename}"
                await attachment.save(image_path)

        await message.channel.send("🤖 Gemini AI가 분석 중입니다...")

        # 분석 및 저장
        try:
            ai_result = analyze_qna(question_text, image_path)

            # DB 저장
            QnALog.objects.create(
                title=f"Discord Q&A ({message.author.name})",
                question_text=question_text,
                ai_answer=ai_result,
                # 이미지 필드 처리는 경로 설정에 따라 다를 수 있음
            )

            await message.reply(f"📝 **분석 결과:**\n\n{ai_result}")
        except Exception as e:
            await message.reply(f"❌ 에러 발생: {str(e)}")


# 3. 봇 실행
bot.run(os.getenv('DISCORD_BOT_TOKEN'))