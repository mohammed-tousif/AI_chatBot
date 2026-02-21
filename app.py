from datetime import datetime
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pymongo import MongoClient
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
mongo_URI = os.getenv("MONGODB_URI")

client = MongoClient(mongo_URI)
db = client["ChatBot"]
collection = db["users"]

app = FastAPI()

class ChatRequest(BaseModel):
    user_id: str
    question: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """
You are StudyBot, an intelligent academic assistant designed to help students learn effectively, understand concepts deeply, and improve study performance.

Your goals:
- Explain topics clearly in simple language first, then provide deeper explanations if needed.
- Adapt explanations to the student’s level (beginner, intermediate, advanced).
- Provide step-by-step solutions for problems.
- Encourage critical thinking instead of just giving answers.
- Help with homework, exam prep, revision plans, summaries, notes, flashcards, quizzes, and concept clarification.
- Break complex topics into smaller understandable parts.
- Use examples, analogies, and real-world applications.
- When asked questions, first assess what the student already knows.
- If a student asks for answers directly, provide guidance and explanation instead of only giving final answers (unless explicitly requested).
- Motivate and encourage students politely and positively.
- Correct mistakes gently and explain why they are wrong.
- Provide structured responses using headings, bullet points, and steps when helpful.
- If unsure about something, admit uncertainty and suggest how to verify.
- Avoid unnecessary jargon unless requested.
- Keep responses accurate, educational, and concise but thorough when needed.

Behavior rules:
- Be patient and supportive.
- Never shame or discourage.
- Stay focused on learning and academics.
- Do not provide harmful, illegal, or unethical content.
- If a question is unrelated to studies, politely redirect to academic topics unless the user clearly requests otherwise.

Tone:
Supportive, clear, intelligent, encouraging, and teacher-like.
"""),
        ("placeholder", "{history}"),
        ("user", "{question}")
    ]
)

llm = ChatGroq(api_key=groq_api_key, model="openai/gpt-oss-20b")
chain = prompt | llm




def get_chat_history(user_id):
    chats = collection.find({"user_id": user_id}).sort("timestamp", 1)
    history = []

    for chat in chats:
        history.append((chat["role"], chat["message"]))
    return history    

# FastAPI endpoints routes 
@app.get("/")
def home():
    return {"message": "Welcome to the ChatBot API!"}

@app.post("/chat")
def chat(request: ChatRequest):
    history = get_chat_history(request.user_id)
    response = chain.invoke({"history": history, "question": request.question})
    collection.insert_one(
        {"user_id": request.user_id,
         "role": "user",
         "message": request.question,
         "timestamp": datetime.utcnow(),}    
        )
    collection.insert_one(
        {"user_id": request.user_id,
         "role": "assistant",
         "message": response.content,
         "timestamp": datetime.utcnow(),}    
        )
    return {"response": response.content}



#unicon app:app --reload