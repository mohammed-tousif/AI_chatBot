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
        ("system", "You are a helpful assistant that answers questions based on the user's input."),
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