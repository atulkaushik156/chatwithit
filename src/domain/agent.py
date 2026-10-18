import os
import hashlib
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

DB_URI = os.getenv("DATABASE_URL")

pool: ConnectionPool = None
checkpointer: PostgresSaver = None

def connect_db():
    """Opens the connection pool with connect_timeout to handle Neon scale-to-zero wakeups."""
    global pool, checkpointer
    if not DB_URI:
        raise ValueError("DATABASE_URL environment variable is not set!")
    
    # Added connect_timeout=10 so Neon compute has time to wake up from sleep
    pool = ConnectionPool(
        conninfo=DB_URI, 
        max_size=10, 
        kwargs={
            "autocommit": True,
            "connect_timeout": 10,
        }
    )
    checkpointer = PostgresSaver(pool)

def close_db():
    """Closes the Neon connection pool when FastAPI shuts down."""
    global pool
    if pool:
        pool.close()

def resolve_user_id(api_key: str) -> str:
    """Returns a unique user_id by SHA-256 hashing the Groq API key (never stores the raw key)."""
    key_hash = hashlib.sha256(api_key.strip().encode()).hexdigest()[:16]
    return f"key_{key_hash}"

def build_graph(api_key: str, model: str = "openai/gpt-oss-20b"):
    llm = ChatGroq(groq_api_key=api_key, model_name=model, temperature=0.7)

    def chat_node(state: MessagesState):
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("chatbot", chat_node)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    
    return builder.compile(checkpointer=checkpointer)

def get_user_threads(user_id: str):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT thread_id, title, created_at FROM user_threads WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cur.fetchall()
            return [{"thread_id": r[0], "title": r[1], "created_at": str(r[2])} for r in rows]

def save_thread_if_new(user_id: str, thread_id: str, first_message: str):
    title = first_message[:35] + ("..." if len(first_message) > 35 else "")
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO user_threads (thread_id, user_id, title)
            VALUES (%s, %s, %s)
            ON CONFLICT (thread_id) DO NOTHING
            """,
            (thread_id, user_id, title)
        )

def get_thread_messages(thread_id: str, api_key: str):
    """Fetches full conversation history for a thread_id from LangGraph's Neon checkpoint tables."""
    graph = build_graph(api_key)
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    
    if not state or not state.values or "messages" not in state.values:
        return []
    
    formatted = []
    for msg in state.values["messages"]:
        if isinstance(msg, HumanMessage):
            formatted.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            formatted.append({"role": "assistant", "content": msg.content})
    return formatted

def invoke_chat(user_id: str, thread_id: str, message: str, api_key: str, model: str):
    save_thread_if_new(user_id, thread_id, message)
    graph = build_graph(api_key, model)
    config = {"configurable": {"thread_id": thread_id}}
    
    result = graph.invoke({"messages": [HumanMessage(content=message)]}, config=config)
    return result["messages"][-1].content