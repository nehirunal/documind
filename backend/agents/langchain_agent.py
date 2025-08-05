from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=api_key)

messages = [
    SystemMessage(content="Sen haberleri özetleyen bir asistansın."),
    HumanMessage(content="Şu haberi özetle:\nSarıyer'de kuryede uyuşturucu bulundu.")
]

response = llm(messages)
print("🧪 Test sonucu:\n", response.content)
