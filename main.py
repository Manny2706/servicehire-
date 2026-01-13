from typing import TypedDict
from langgraph.graph import StateGraph,END
from langchain_openai import ChatOpenAI
import json
import os
from dotenv import load_dotenv

load_dotenv()

# 1. LLM SETUP (API key must be in environment)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# 2. STATE DEFINITION

class AgentState(TypedDict):
    user_message: str
    intent: str
    name: str
    email: str
    platform: str
    requested_field: str
    response: str

# 3. INTENT DETECTION (LLM)
def detect_intent(state: AgentState):
    # If already in lead capture, do not re-detect intent
    if state.get("intent") == "high_intent" and  is_lead_in_progress(state):
        return state

    prompt = f"""
    You are an intent classification system.

    Classify the user message into ONE of these intents:
    - greeting
    - pricing ( if asked about pricing, plans,plan details or costs )
    - high_intent( if user shows strong interest in buying or signing up for a service or said about basic and pro plans or numeric values of 1,2,3 etc)
    - unknown

    User message: "{state['user_message']}"

    Return ONLY the intent name.
    """

    intent = llm.invoke(prompt).content.strip().lower()
    if not(intent=="unknown"):
        state["intent"] = intent
    return state


def handle_greeting(state: AgentState):
    prompt = """
    You are a friendly SaaS assistant.
    Greet the user briefly and ask how you can help.
    """

    response = llm.invoke(prompt)
    state["response"] = response.content.strip()
    return state

# 4. RAG: ANSWER FROM KNOWLEDGE BASE

def answer_from_knowledge(state: AgentState):
    with open("knowledge.json") as f:
        data = json.load(f)

    if state["intent"] == "pricing":
        context = f"""
        Pricing Information:
        Basic Plan: {data['pricing']['Basic']}
        Pro Plan: {data['pricing']['Pro']}
        """

        prompt = f"""
        You are a helpful SaaS sales assistant.

        Use ONLY the information below to answer the user.
        Do NOT add extra details.

        {context}

        User question: {state['user_message']}
        """

        response = llm.invoke(prompt)
        state["response"] = response.content.strip()

    return state

# 5. LEAD COLLECTION + TOOL EXECUTION

def mock_lead_capture(name, email, platform):
    print(f"Lead captured successfully: {name}, {email}, {platform}")
    # In real scenario, integrate with CRM or database here.
    # reinitialize state after lead capture
    state = {
        "user_message": "",
        "intent": "",
        "name": "",
        "email": "",
        "platform": "",
        "requested_field": "",
        "response": ""
    }




def extract_user_details(state: AgentState):
    text = state["user_message"].strip()
    field = state.get("requested_field")

    if field == "email":
        if "@" in text and "." in text:
            state["email"] = text

    elif field == "platform":
        for platform in ["youtube", "instagram", "tiktok"]:
            if platform in text.lower():
                state["platform"] = platform.capitalize()

    elif field == "name":
        if text.replace(" ", "").isalpha():
            state["name"] = text

    return state

def is_lead_in_progress(state: AgentState) -> bool:
    return not (
        state.get("name") and
        state.get("email") and
        state.get("platform")
    )

def ask_lead_details(state: AgentState):
    missing = []

    if not state.get("name"):
        missing.append("name")
    if not state.get("email"):
        missing.append("email")
    if not state.get("platform"):
        missing.append("platform")

    if missing:
        field = missing[0]   # ask ONE at a time
        state["requested_field"] = field

        prompt = f"""
        You are a friendly SaaS sales assistant.
        Ask the user politely for their {field}.
        Ask in one short sentence.
        """

        state["response"] = llm.invoke(prompt).content.strip()
        return state

    # all collected
    mock_lead_capture(
        state["name"],
        state["email"],
        state["platform"]
    )

    state["requested_field"] = ""
    state["response"] = f"Thanks {state['name']}! Your details have been captured successfully. We will reach out to you soon. Have a great day!"
    return state


# 6. ROUTING LOGIC

def route(state: AgentState):
    if state.get("intent") == "high_intent" and  is_lead_in_progress(state):
        return "extract"

    if state["intent"] == "pricing":
        return "knowledge"

    if state["intent"] in ["greeting", "unknown"]:
        return "greeting"

    return "end"


# 7. BUILD LANGGRAPH

graph = StateGraph(AgentState)
graph.add_node("intent", detect_intent)
graph.add_node("greeting", handle_greeting)
graph.add_node("knowledge", answer_from_knowledge)
graph.add_node("extract", extract_user_details)
graph.add_node("lead", ask_lead_details)


graph.set_entry_point("intent")
graph.add_conditional_edges(
    "intent",
    route,
    {
        "greeting": "greeting",
        "knowledge": "knowledge",
        "extract": "extract",
        "end": END
    }
)

graph.add_edge("extract", "lead")
graph.add_edge("greeting", END)
graph.add_edge("knowledge", END)
graph.add_edge("lead", END)

app = graph.compile()

# 8. RUN CHAT LOOP
if __name__ == "__main__":

    # initialize state ONCE (important)
    state = {
        "user_message": "",
        "intent": "",
        "name": "",
        "email": "",
        "platform": "",
        "requested_field": "",
        "response": ""
    }

    while True:
        user_input = input("User: ")

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting chat.")
            break

        # update only the user message
        state["user_message"] = user_input

        # run LangGraph
        state = app.invoke(state)

        print("\nAgent:", state["response"])
