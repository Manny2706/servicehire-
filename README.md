# ServiceHire - SaaS Chatbot Agent

An intelligent chatbot built with LangGraph and LangChain that handles customer inquiries, pricing questions, and lead capture for a SaaS platform.

## Features

- **Intent Detection**: Classifies user messages into greeting, pricing, high_intent, or unknown
- **Knowledge Base**: Answers pricing questions using RAG (Retrieval-Augmented Generation)
- **Lead Capture**: Systematically collects user details (name, email, platform preference)
- **Multi-turn Conversation**: Maintains state across multiple interactions
- **LLM-Powered**: Uses OpenAI's GPT-4o-mini for intelligent responses

## Project Structure

```
servicehire/
├── main.py              # Main chatbot logic with LangGraph workflow
├── knowledge.json       # Knowledge base with pricing and policy information
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (API keys)
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Setup

### Prerequisites
- Python 3.8+
- OpenAI API key

### Installation

1. Clone or navigate to the project directory:
```bash
cd servicehire
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/Scripts/activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

Run the chatbot:
```bash
python main.py
```

The chatbot will start an interactive loop where you can:
- Ask greetings
- Inquire about pricing
- Express interest in signing up (triggers lead capture)
- Exit with `exit` or `quit`

### Example Interactions

**Greeting:**
```
User: Hi, how are you?
Agent: Hello! I'm here to help. What can I assist you with today?
```

**Pricing Inquiry:**
```
User: What are your plans?
Agent: [Retrieves pricing from knowledge base]
```

**Lead Capture:**
```
User: I'm interested in the Pro plan
Agent: What's your name?
User: John Doe
Agent: What's your email?
User: john@example.com
Agent: Which platform do you use? (YouTube, Instagram, TikTok)
User: YouTube
Agent: Thanks John! Your details have been captured successfully.
```

## How to Run Locally

- Create and activate the virtual environment: `python -m venv venv` then `venv\Scripts\activate` on Windows.
- Install dependencies: `pip install -r requirements.txt`.
- Add your OpenAI key to `.env`: `OPENAI_API_KEY=your_api_key_here`.
- Start the agent: `python main.py`.

## Architecture Explanation (≈200 words)

This project uses LangGraph to orchestrate a deterministic, node-based workflow around the LLM. LangGraph was chosen over a free-form agent loop (e.g., AutoGen-style tool calling) because the conversation here is a narrow funnel: detect intent, answer pricing from a fixed knowledge base, or collect lead details step by step. A graph keeps the path explicit and auditable, avoids unbounded tool calls, and makes it trivial to add or remove states without changing the core loop. State is kept in a typed dict (`AgentState`) that flows through every node; each node mutates only the fields it owns (e.g., `detect_intent` sets `intent`, `answer_from_knowledge` sets `response`, `extract_user_details` sets `name/email/platform`). The router examines the current state to decide the next edge, so multi-turn lead capture works by looping through `extract` → `lead` until all required fields are present. Because the graph is compiled once and the same state dict is reused across turns, the agent preserves context (missing fields, previous intent) without any external store. If you later add persistence (database for leads) or more branches (support, cancellations), you simply register new nodes and edges; the state contract stays stable, keeping the system predictable and easy to test.

## WhatsApp Deployment (Webhooks)

1) Obtain WhatsApp API access (Meta WhatsApp Business Cloud API or a BSP). Configure a webhook URL that Meta will call on incoming messages. 
2) Expose an HTTPS endpoint (e.g., FastAPI/Flask) that accepts the webhook payload, extracts the user message, and looks up the conversation state (by WhatsApp user ID) from a store (Redis/DB). 
3) Pass the message and stored state into `app.invoke(state)` from `main.py`; capture the updated state and agent response. 
4) Persist the updated state keyed by the sender ID so the next webhook call continues the same conversation. 
5) Send the agent response back via the WhatsApp Send Message API. 
6) Verify the webhook token with Meta, handle retries idempotently, and log failures. 
Tip: keep the `AgentState` JSON-serializable so it can be stored directly; avoid blocking the webhook handler by offloading LLM calls to a worker queue if latency becomes an issue.

## Graph Flow

The chatbot uses a state machine with the following flow:

```
START
  ↓
[INTENT] - Intent Detection
  ↓
  ├→ [GREETING] → END
  ├→ [KNOWLEDGE] → END
  └→ [EXTRACT] → [LEAD] → END
```

## Configuration

### Knowledge Base (knowledge.json)
Edit `knowledge.json` to update pricing and policies:
```json
{
  "pricing": {
    "Basic": "Plan details here",
    "Pro": "Plan details here"
  },
  "policies": {
    "refund": "Refund policy",
    "support": "Support details"
  }
}
```

### LLM Settings (main.py)
Adjust the LLM in `main.py`:
```python
llm = ChatOpenAI(
    model="gpt-4o-mini",  # Change model if needed
    temperature=0,         # 0 = deterministic, 1 = creative
    openai_api_key=os.getenv("OPENAI_API_KEY")
)
```

## Dependencies

- `langgraph` - State machine framework
- `langchain` - LLM framework
- `langchain-openai` - OpenAI integration
- `python-dotenv` - Environment variable management

## Future Enhancements

- Persistent storage for captured leads
- Multi-language support
- Advanced NLP for better intent detection
- Database integration for knowledge base
- Admin dashboard for lead management

## License

MIT License
