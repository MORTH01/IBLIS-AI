# 🤖 Personal AI Assistant
> Powered by Claude API — knows you, remembers everything, works for you.

---

## What This Does

| Feature | Description |
|---|---|
| 💬 Chat | Talks to you with full memory of past conversations |
| 🧠 Memory | Semantically searches your chat history to give context-aware answers |
| 👤 Profile | Stores everything about you — your work, skills, projects, goals |
| ☀️ Daily Briefing | AI-generated morning briefing based on your tasks and profile |
| ✅ Tasks | Full to-do list with priorities — AI sees these and reminds you |

---

## Project Structure

```
personal-ai/
├── backend/
│   ├── main.py            ← FastAPI app (all API routes)
│   ├── memory.py          ← SQLite + ChromaDB memory system
│   ├── profile_manager.py ← User profile & task storage
│   ├── requirements.txt   ← Python dependencies
│   └── .env.example       ← Environment variable template
│
└── frontend/
    └── index.html         ← Complete UI (open directly in browser)
```

---

## ⚡ Step-by-Step Setup

### Step 1 — Get Your Claude API Key

1. Go to **https://console.anthropic.com/**
2. Sign up / Log in
3. Click **"API Keys"** in the left sidebar
4. Click **"Create Key"**
5. Copy the key — it starts with `sk-ant-...`
6. **Keep it safe — don't share it!**

---

### Step 2 — Install Python

Check if you have Python 3.10+:
```bash
python --version
# or
python3 --version
```

If not, download from **https://python.org/downloads/**
Make sure to check ✅ **"Add Python to PATH"** during installation.

---

### Step 3 — Set Up the Backend

Open a terminal and navigate to the backend folder:

```bash
cd personal-ai/backend
```

**Create a virtual environment** (keeps things clean):
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal now.

**Install all dependencies:**
```bash
pip install -r requirements.txt
```

This installs: FastAPI, Anthropic SDK, ChromaDB, SQLite support, and more.
*Takes 1–3 minutes.*

---

### Step 4 — Add Your API Key

Copy the example env file:
```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

Open `.env` in any text editor and replace the placeholder:
```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

Save the file.

---

### Step 5 — Start the Backend

```bash
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

✅ **Backend is running!** Leave this terminal open.

---

### Step 6 — Open the Frontend

1. Navigate to the `frontend/` folder in your file explorer
2. Double-click **`index.html`**
3. It opens in your browser automatically

OR open it from terminal:
```bash
# Windows
start frontend/index.html

# Mac
open frontend/index.html

# Linux
xdg-open frontend/index.html
```

---

### Step 7 — Set Up Your Profile

1. Click **"👤 My Profile"** in the left sidebar
2. Fill in your:
   - Name
   - Role/Title
   - About you (the more detail, the better your AI knows you)
   - Current projects
   - Skills
   - Goals
3. Click **"💾 Save Profile"**

This becomes the foundation of what your AI knows about you.

---

### Step 8 — Start Talking!

Click **"💬 Chat"** and start a conversation. Tell your AI:
- What you're working on today
- What your biggest challenges are
- What you want to get done

The AI will remember **everything** you tell it across all conversations.

---

## 🧠 How Memory Works

Every message you send is:
1. **Stored in SQLite** — exact conversation history
2. **Embedded in ChromaDB** — semantic vector search

When you send a new message, the AI:
1. Searches past conversations for relevant context
2. Loads your profile
3. Injects all of it into the prompt before responding

So even if you talked about something 3 weeks ago, it can recall it.

---

## ☀️ Using the Daily Briefing

1. Click **"☀️ Daily Briefing"**
2. Click **"⚡ Generate Briefing"**

The AI generates a personalized morning briefing based on:
- Your profile
- Your current task list
- What's high priority today

**Pro tip:** Run this every morning before starting work.

---

## ✅ Task Management

1. Click **"✅ Tasks"**
2. Click **"＋ Add Task"**
3. Set title, priority (High/Medium/Low), due date
4. Click the checkbox to mark done
5. Click 🗑 to delete

Your AI **sees all your tasks** — so you can ask things like:
- *"What should I focus on today?"*
- *"I only have 2 hours — what's most important?"*
- *"Am I on track with my projects?"*

---

## 💡 Things to Ask Your AI

```
"What did we talk about last time regarding my RMTI-RD research?"
"Summarize my current projects"
"What's the most important thing I should work on today?"
"Help me prioritize my tasks"
"I'm feeling overwhelmed, what should I do first?"
"Draft an email about [topic] in my style"
"Remind me what my goals are"
```

---

## 🔧 Running Again After Restart

Every time you want to use it:

```bash
# 1. Go to backend folder
cd personal-ai/backend

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Start the server
uvicorn main:app --reload --port 8000

# 4. Open frontend/index.html in browser
```

---

## 🚀 Future Upgrades (Phase 2)

Once this is working, here's what you can add:

| Upgrade | How |
|---|---|
| 📧 Gmail integration | Connect Gmail API → AI reads your emails |
| 📅 Google Calendar | AI knows your schedule automatically |
| 📰 Real news | Add NewsAPI key → briefing includes actual headlines |
| 🔔 Desktop notifications | Add daily cron job for auto-briefing |
| 📱 Mobile access | Deploy backend to Railway/Render (free tier) |
| 🧬 Fine-tuning | Train Llama on your conversations for a fully custom model |

---

## ❗ Troubleshooting

**"Could not connect to backend"**
→ Make sure the backend terminal is still running (`uvicorn main:app --reload`)

**"ANTHROPIC_API_KEY not found"**
→ Check your `.env` file exists in the `backend/` folder with the correct key

**ChromaDB install fails**
→ Try: `pip install chromadb --no-deps` then `pip install hnswlib`
→ Or: the app works without ChromaDB (falls back to keyword search)

**Port 8000 already in use**
→ Use a different port: `uvicorn main:app --reload --port 8001`
→ Update the `API` variable in `frontend/index.html` to match

---

## 🔒 Privacy

- Everything runs **locally on your machine**
- Your conversations are stored in `backend/data/` (SQLite + ChromaDB)
- Only the message content is sent to Anthropic's API
- Nothing is stored on any cloud (unless you deploy it yourself)

---

*Built with FastAPI + Claude API + ChromaDB + SQLite*
