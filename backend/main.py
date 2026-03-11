from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from groq import Groq
import json, os
from datetime import datetime
from memory import MemoryManager
from profile_manager import ProfileManager

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

client = Groq(api_key=os.environ["GROQ_API_KEY"])
memory = MemoryManager()
profile = ProfileManager()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class TaskRequest(BaseModel):
    title: str
    priority: str = "medium"
    due: Optional[str] = None
    notes: Optional[str] = None

class ProfileUpdate(BaseModel):
    data: dict

@app.post("/api/chat")
async def chat(req: ChatRequest):
    user_profile = profile.get_profile()
    relevant_memories = memory.search(req.message, n_results=8)
    session_history = memory.get_session_history(req.session_id, limit=20)
    today = datetime.now().strftime("%A, %B %d, %Y - %I:%M %p")
    memory_block = "\n".join(f"- {m}" for m in relevant_memories) if relevant_memories else "No past memories yet."

    system_prompt = f"""You are a deeply personal AI assistant for {user_profile.get('name', 'the user')}.
You have persistent memory and remember everything from all past conversations.

USER PROFILE:
{json.dumps(user_profile, indent=2)}

RELEVANT MEMORIES FROM PAST CONVERSATIONS:
{memory_block}

TODAY: {today}

INSTRUCTIONS:
- Reference past conversations naturally when relevant
- If the user updated something before (schedule, goals, preferences), remember and apply it
- Be direct, warm, and genuinely helpful
- Give specific actionable advice based on what you know about them
- Use markdown formatting for clarity
- Never say you cannot remember - you have memory, use it"""

    messages = session_history + [{"role": "user", "content": req.message}]
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=2048,
        messages=[{"role": "system", "content": system_prompt}] + messages
    )
    reply = response.choices[0].message.content
    memory.store_conversation(req.session_id, req.message, reply)
    _try_extract_profile(req.message, user_profile)
    return {"response": reply, "session_id": req.session_id}

def _try_extract_profile(message: str, current_profile: dict):
    msg = message.lower()
    updates = {}
    if "my name is" in msg:
        parts = message.split("my name is", 1)
        if len(parts) > 1:
            name = parts[1].strip().split()[0].strip(".,!")
            updates["name"] = name
    if any(k in msg for k in ["i work as", "i am a", "i'm a"]):
        for kw in ["i work as", "i am a", "i'm a"]:
            if kw in msg:
                parts = message.lower().split(kw, 1)
                role = parts[1].strip().split(".")[0].strip()[:80]
                updates["role"] = role
                break
    if updates:
        profile.update_profile(updates)

@app.get("/api/briefing")
async def get_briefing():
    user_profile = profile.get_profile()
    tasks = profile.get_tasks()
    pending = [t for t in tasks if not t.get("done")]
    prompt = f"""Write a personal daily briefing for {user_profile.get('name', 'the user')}.
Profile: {json.dumps(user_profile)}
Tasks: {json.dumps(pending)}
Today: {datetime.now().strftime('%A, %B %d, %Y')}
Sections: Good morning greeting, Top 3 priorities, Task overview, Focus tip."""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return {"briefing": response.choices[0].message.content}

@app.get("/api/sessions")
async def get_sessions():
    return {"sessions": memory.get_sessions()}

@app.get("/api/sessions/{session_id}")
async def get_session_messages(session_id: str):
    return {"messages": memory.get_session_history(session_id, limit=200)}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    memory.delete_session(session_id)
    return {"status": "deleted"}

@app.get("/api/profile")
async def get_profile():
    return profile.get_profile()

@app.put("/api/profile")
async def update_profile(req: ProfileUpdate):
    profile.update_profile(req.data)
    return {"status": "updated"}

@app.get("/api/tasks")
async def get_tasks():
    return {"tasks": profile.get_tasks()}

@app.post("/api/tasks")
async def add_task(req: TaskRequest):
    return {"status": "added", "task": profile.add_task(req.dict())}

@app.put("/api/tasks/{task_id}/done")
async def complete_task(task_id: str):
    profile.complete_task(task_id)
    return {"status": "completed"}

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    profile.delete_task(task_id)
    return {"status": "deleted"}

@app.get("/api/memories")
async def get_memories(limit: int = 20):
    return {"memories": memory.get_recent(limit)}

@app.get("/")
async def root():
    return {"status": "running"}
