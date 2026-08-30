import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from tools.calculator import calculator
from tools.currency import convert_currency
from tools.distance import get_distance
from tools.google_calendar import create_event
from tools.memory import get_preference, save_preference
from tools.net import system_certs_context, use_system_certs
from tools.search import web_search
from tools.weather import get_weather

load_dotenv()

TOOLS = [
    calculator,
    convert_currency,
    get_weather,
    save_preference,
    get_preference,
    web_search,
    get_distance,
    create_event,
]


def _llm_client_args() -> dict | None:
    """Trust the OS certificate store instead of certifi's bundled CA list.

    Some environments (e.g. AV software doing TLS inspection) inject a root
    CA into the OS trust store that certifi doesn't know about, breaking
    HTTPS calls to the Gemini API with CERTIFICATE_VERIFY_FAILED. Set
    USE_SYSTEM_CERTS=1 to build the underlying httpx client against the OS
    trust store (via OpenSSL's native store enumeration) instead.
    """
    if not use_system_certs():
        return None
    return {"verify": system_certs_context()}


llm = ChatGoogleGenerativeAI(
    model=os.getenv("GOOGLE_MODEL", "gemini-3.5-flash-lite"),
    client_args=_llm_client_args(),
)
llm_with_tools = llm.bind_tools(TOOLS)


def call_model(state: MessagesState) -> MessagesState:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


graph_builder = StateGraph(MessagesState)
graph_builder.add_node("agent", call_model)
graph_builder.add_node("tools", ToolNode(TOOLS))
graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", tools_condition)
graph_builder.add_edge("tools", "agent")
agent_graph = graph_builder.compile()

app = FastAPI(title="AI Travel Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    messages = [
        SystemMessage(
            content=(
                f"The current user's id is '{request.user_id}'. When calling "
                "save_preference or get_preference, pass this exact value as "
                "user_id."
            )
        ),
        HumanMessage(content=request.message),
    ]
    result = agent_graph.invoke({"messages": messages})
    reply = result["messages"][-1].text
    return ChatResponse(response=reply)
