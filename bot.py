import os
import time
from collections import defaultdict
import discord
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv() 

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_KEY")
ALLOWED_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

MAX_HISTORY = 10
INACTIVITY_TIMEOUT = 1800

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

ai_client = OpenAI(api_key=OPENAI_API_KEY)

# Conversation history { user_id: { "messages": [...], "last_active": timestamp } }
conversations = defaultdict(lambda: {"messages": [], "last_active": 0})

def add_message(user_id, role, content):
    now = time.time()
    convo = conversations[user_id]

    if now - convo["last_active"] > INACTIVITY_TIMEOUT:
        convo["messages"] = []

    convo["messages"].append({"role": role, "content": content})
    convo["last_active"] = now

    if len(convo["messages"]) > MAX_HISTORY:
        convo["messages"] = convo["messages"][-MAX_HISTORY:]

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id != ALLOWED_CHANNEL_ID:
        return
    
    if client.user not in message.mentions:
        return
    
    user_id = str(message.author.id)
    user_message = message.content.replace(f"<@{client.user.id}>", "").strip()
    if not user_message:
        await message.channel.send("Yes? What do you need help with?")
        return

    add_message(user_id, "user", user_message)

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful AI coding teaching assistant. Provide help and fix code like a TA. Be very concise and conversational."}
            ] + conversations[user_id]["messages"],
            max_tokens=500,
        )

        reply = response.choices[0].message.content

        add_message(user_id, "assistant", reply)

        if len(reply) <= 2000:
            await message.channel.send(reply)
        else:
            for i in range(0, len(reply), 2000):
                await message.channel.send(reply[i:i+2000])

    except Exception as e:
        print(f"❌ Error: {e}")
        await message.channel.send("Hmm, something went wrong. Please try again later.")

client.run(DISCORD_TOKEN)
