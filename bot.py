from os import getenv

print("BOT FILE LOADED")
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import aiohttp
from pyparsing import with_class

# 1. 환경 변수 및 장고 설정 로드
load_dotenv()
print("2️⃣ imports done")
token = os.getenv("DISCORD_BOT_TOKEN")
print("4️⃣ token =", token)
DJANGO_API_URL = "http://127.0.0.1:8000/archiver/qna/"


# 2. 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
print("5️⃣ bot object created")

@bot.event
async def on_ready():
    print(f'✅ 봇 로그인 성공: {bot.user.name}')
print("6️⃣ before bot.run()")
async def call_django_api(question_text):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            DJANGO_API_URL,
                json={"question_text": question_text},
                timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            return await resp.json()


@bot.event
async def on_message(message):
    # 봇 본인의 메시지는 무시
    if message.author == bot.user:
        return

    if message.content.startswith('!질문'):
        question_text = message.content.replace('!질문', '').strip()

        if not question_text:
            await message.reply("❓ 질문 내용을 입력해주세요")
            return

        status_msg = await message.channel.send("🤖 분석 중입니다...")

        try:
            result = await call_django_api(question_text)

            if result.get("status") == "verified":
                await message.reply(
                f"이 질문은 이미 정리되어 있습니다!\n"
                f"노션 링크 {result.get('notion_url')}"
                )

            elif result.get("status") == "duplicate":
                await message.reply(f"📎 이전 질문 답변입니다:\n{result['ai_answer']}")

            elif result.get("status") == "new":
                await message.reply(f"📝 분석 결과:\n{result['ai_answer']}")

            else:
                await message.reply("⚠️ 알 수 없는 서버 응답입니다.")

        except Exception as e:
            await message.reply(f"❌ 서버 오류: {str(e)[:200]}")

        finally:
            await status_msg.delete()

    # 3. 봇 실행
bot.run(os.getenv('DISCORD_BOT_TOKEN'))
print("7️⃣ after bot.run()")