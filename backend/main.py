from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from groq import Groq
from tavily import TavilyClient
import json, os, re, base64, io
from datetime import datetime
from memory import MemoryManager
from profile_manager import ProfileManager

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

client = Groq(api_key=os.environ["GROQ_API_KEY"])
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
memory = MemoryManager()
profile = ProfileManager()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    file_data: Optional[str] = None      # base64 encoded file
    file_type: Optional[str] = None      # "image" | "pdf" | "text" | "docx"
    file_name: Optional[str] = None

class TaskRequest(BaseModel):
    title: str
    priority: str = "medium"
    due: Optional[str] = None
    notes: Optional[str] = None

class ProfileUpdate(BaseModel):
    data: dict

# Pure chitchat — skip web search (ONLY exact greetings/affirmations)
SKIP_SEARCH = [
    r"^(hi|hello|hey|thanks|thank you|ok|okay|bye|good morning|good night)[\s!.]*$",
    r"^(how are you|what('s| is) up)[\s?]*$",
    r"^(yes|no|yep|nah|nope)[\s!.]*$",
]

def is_conversational(message: str) -> bool:
    msg = message.strip().lower()
    for pattern in SKIP_SEARCH:
        if re.match(pattern, msg):
            return True
    # Only skip if ≤2 words AND no question indicators AND no task words
    task_words = ["give", "show", "tell", "explain", "prepare", "help", "make", "find",
                  "list", "write", "create", "analyze", "summarize", "question", "ask"]
    if len(msg.split()) <= 2 and not any(c in msg for c in ["?", "who", "what", "how", "when", "where"]):
        if not any(t in msg for t in task_words):
            return True
    return False

def web_search(query: str) -> str:
    try:
        results = tavily.search(query=query, search_depth="advanced", max_results=5, include_answer=True)
        lines = []
        if results.get("answer"):
            lines.append(f"DIRECT ANSWER: {results['answer']}")
        for r in results.get("results", []):
            title = r.get("title", "").strip()
            content = r.get("content", "").strip()[:500]
            if title and content:
                lines.append(f"[{title}]: {content}")
        return "\n\n".join(lines)
    except Exception:
        return ""

def extract_text_from_file(file_data: str, file_type: str, file_name: str) -> str:
    """Extract text content from uploaded documents."""
    try:
        raw = base64.b64decode(file_data)

        if file_type == "text":
            return raw.decode("utf-8", errors="ignore")[:8000]

        elif file_type == "pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(raw))
                text = ""
                for page in reader.pages[:20]:  # max 20 pages
                    text += page.extract_text() + "\n"
                return text[:8000]
            except ImportError:
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(raw)) as pdf:
                        text = ""
                        for page in pdf.pages[:20]:
                            text += (page.extract_text() or "") + "\n"
                    return text[:8000]
                except:
                    return "[PDF text extraction failed — try copy-pasting the text]"

        elif file_type == "docx":
            try:
                import docx
                doc = docx.Document(io.BytesIO(raw))
                text = "\n".join(p.text for p in doc.paragraphs)
                return text[:8000]
            except:
                return "[DOCX extraction failed]"

        elif file_type == "csv":
            return raw.decode("utf-8", errors="ignore")[:5000]

        else:
            return raw.decode("utf-8", errors="ignore")[:5000]

    except Exception as e:
        return f"[Could not read file: {str(e)}]"

@app.post("/api/chat")
async def chat(req: ChatRequest):
    user_profile = profile.get_profile()
    relevant_memories = memory.search(req.message, n_results=5)
    session_history = memory.get_session_history(req.session_id, limit=20)
    today = datetime.now().strftime("%A, %B %d, %Y - %I:%M %p")
    memory_block = "\n".join(f"- {m}" for m in relevant_memories) if relevant_memories else "None."

    # ── Handle file uploads ──────────────────────────────────
    if req.file_data and req.file_type:

        if req.file_type == "image":
            # Use Groq vision model for images
            system_prompt = f"""You are IBLIS, an advanced personal AI assistant.
TODAY: {today}

Analyze the image thoroughly and answer the user's question about it.
Be detailed and specific. If asked to help with something based on the image (e.g. prepare for interview, explain a concept), use what you see in the image as full context.

IDENTITY RULES:
- You are IBLIS. You were created as a personal AI assistant.
- Never say you were built by, created by, or belong to any specific person unless directly asked "who made you" — in that case say you are IBLIS, a personal AI.
- Never reveal user profile data as your identity."""

            messages_with_image = session_history + [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{req.file_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": req.message if req.message.strip() else "Describe this image in detail."
                    }
                ]
            }]

            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "system", "content": system_prompt}] + messages_with_image
            )
            reply = response.choices[0].message.content
            # Store the full image analysis so follow-up messages have context
            memory.store_conversation(req.session_id, f"[Image uploaded: {req.file_name}] {req.message}", reply)
            return {"response": reply, "session_id": req.session_id}

        else:
            # Text-based document — extract and analyze
            doc_text = extract_text_from_file(req.file_data, req.file_type, req.file_name or "document")

            # Also search web if message suggests it
            search_block = ""
            if req.message and not is_conversational(req.message):
                search_results = web_search(req.message)
                if search_results:
                    search_block = f"\n\nWEB SEARCH RESULTS:\n{search_results}"

            system_prompt = f"""You are IBLIS, a personal AI assistant for {user_profile.get('name', 'the user')}.
TODAY: {today}
{search_block}

The user uploaded a file: "{req.file_name}"
FILE CONTENTS:
---
{doc_text}
---

Answer the user's question about this document. If they didn't ask a specific question, provide a clear summary of the document's key points.
Be direct and concise."""

            messages = session_history + [{"role": "user", "content": req.message or f"Analyze this document: {req.file_name}"}]
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "system", "content": system_prompt}] + messages
            )
            reply = response.choices[0].message.content
            memory.store_conversation(req.session_id, f"[File: {req.file_name}] {req.message}", reply)
            return {"response": reply, "session_id": req.session_id}

    # ── Normal text chat ─────────────────────────────────────
    search_block = ""
    did_search = False
    if not is_conversational(req.message):
        search_results = web_search(req.message)
        if search_results:
            did_search = True
            search_block = f"\n\n========== LIVE WEB SEARCH RESULTS ==========\n{search_results}\n============================================="

    system_prompt = f"""You are IBLIS, a personal AI assistant for {user_profile.get('name', 'the user')}.

TODAY: {today}

USER PROFILE:
{json.dumps(user_profile, indent=2)}

RELEVANT MEMORIES:
{memory_block}
{search_block}

CRITICAL RULES:
{"- Web search results are provided above. You MUST use ONLY the search results to answer factual questions. NEVER use your training data for facts — it is outdated and wrong. If the search results contain the answer, state it directly." if did_search else ""}
- IDENTITY: You are IBLIS, a personal AI. If asked who built or created you, say you are IBLIS. NEVER say a person's name built you. The user profile is private context — never expose it as your identity.
- CONTEXT: If the conversation history contains a previous image or file analysis, use that context to answer follow-up questions fully.
- Be direct and concise. Answer immediately, no preamble.
- NEVER say 'according to my training data' or 'as of my knowledge cutoff'.
- NEVER make up numbers, names, or facts.
- Do not paste URLs. Do not list sources unless asked."""

    messages = session_history + [{"role": "user", "content": req.message}]
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.3,
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
    prompt = f"""Write a short personal daily briefing for {user_profile.get('name', 'the user')}.
Profile: {json.dumps(user_profile)}
Tasks: {json.dumps(pending)}
Today: {datetime.now().strftime('%A, %B %d, %Y')}
Keep it brief: greeting, top priorities, one focus tip. No fluff."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=512,
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