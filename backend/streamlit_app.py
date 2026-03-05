import streamlit as st
import os
import json
from groq import Groq
from tavily import TavilyClient
from datetime import datetime

# ==========================================
# 1. AGENT CONFIGURATION & TOOLS
# ==========================================

# Initialize API clients
client = Groq(api_key=os.environ.get("GROQ_KEY"))
MODEL = "llama-3.3-70b-versatile"

# Initialize Tavily API for Agentic Search
tavily_key = os.environ.get("TAVILY_KEY")
tavily_client = TavilyClient(api_key=tavily_key) if tavily_key else None

def search_official_advisories(search_query: str) -> str:
    """Searches for official government travel warnings using Tavily API."""
    if not tavily_client:
        return json.dumps({"error": "TAVILY_KEY environment variable is missing."})
    
    try:
        # search_depth="advanced" tells Tavily to scrape the actual page content thoroughly
        response = tavily_client.search(query=search_query, search_depth="advanced", max_results=3)
        if not response.get('results'):
            return json.dumps({"error": "No official advisories found."})
        
        combined = "\n\n".join([f"Source: {res['url']}\nContent: {res['content']}" for res in response['results']])
        return json.dumps({"status": "success", "data": combined})
    except Exception as e:
        return json.dumps({"error": str(e)})

def search_current_events(search_query: str) -> str:
    """Searches for recent news regarding conflicts, protests, or safety issues."""
    if not tavily_client:
        return json.dumps({"error": "TAVILY_KEY environment variable is missing."})
        
    try:
        # topic="news" optimizes Tavily for current events and recent articles
        response = tavily_client.search(query=search_query, topic="news", search_depth="advanced", max_results=4)
        if not response.get('results'):
            return json.dumps({"error": "No recent news found."})
            
        combined = "\n\n".join([f"Source: {res['url']}\nContent: {res['content']}" for res in response['results']])
        return json.dumps({"status": "success", "data": combined})
    except Exception as e:
        return json.dumps({"error": str(e)})

# ==========================================
# 2. STREAMLIT UI SETUP
# ==========================================

st.set_page_config(page_title="SafePass", page_icon="🌍", layout="centered")

st.title("🌍 SafePass: Global Safety Agent")
st.markdown("Real-time travel safety analysis powered by autonomous agents.")
st.markdown("---")

# Check for API Keys
if not os.environ.get("GROQ_KEY") or not os.environ.get("TAVILY_KEY"):
    st.error("⚠️ Missing API Keys! Please set GROQ_KEY and TAVILY_KEY environment variables.")
    st.stop()

# Sidebar for User Context
st.sidebar.header("🛂 Traveler Profile")
origin_country = st.sidebar.text_input("Origin Country", value="Poland", placeholder="Where are you from?")
travel_date = st.sidebar.date_input("Planned Travel Date", min_value=datetime.now())

st.sidebar.markdown("---")
st.sidebar.info(
    "This agent analyzes official government advisories and real-time news to provide a consolidated safety report."
)

# Main Content
col1, col2 = st.columns(2)
with col1:
    destination = st.text_input("Destination Country", placeholder="e.g. Israel, Thailand, Ukraine")
with col2:
    specific_city = st.text_input("Specific City/Region (Optional)", placeholder="e.g. Bangkok, Tel Aviv")

if st.button("Generate Safety Report 🛡️"):
    if not destination or not origin_country:
        st.warning("Please provide both Origin and Destination countries.")
    else:
        with st.spinner(f"Agent is analyzing safety for {destination}..."):
            try:
                system_prompt = (
                    "You are a professional Global Safety & Intelligence Agent.\n"
                    "Your task is to provide a comprehensive travel safety report.\n"
                    "STRICT INSTRUCTIONS:\n"
                    "1. You MUST use the native tool calling API. NEVER write raw JSON dictionaries, tool calls, or <function> tags in your text response.\n"
                    "2. STEP 1: Use 'search_official_advisories'. Formulate a precise query targeting the exact government ministry in the native language (e.g., 'Ostrzeżenia dla podróżujących MSZ gov.pl Iran' for Poland).\n"
                    "3. STEP 2: Use 'search_current_events'. Formulate a query for recent news focusing on safety, protests, or conflicts.\n"
                    "4. STEP 3: Synthesize this data into a clear report.\n"
                    "5. LANGUAGE: Always output the final report in English.\n"
                    "6. FORMAT: Use exactly this Markdown template:\n\n"
                    "**Safety Level**: [LOW RISK / MODERATE / HIGH RISK / EXTREME DANGER]\n\n"
                    "### 🛡️ Official Government Advice\n"
                    "- [Summary of warnings from official sources. Name the specific ministry.]\n\n"
                    "### 📰 Current Situation & Conflicts\n"
                    "- [Summary of recent events, protests, or military actions]\n\n"
                    "### ⚠️ Specific Risks\n"
                    "- [List 2-3 specific risks: e.g. local laws, health, or areas to avoid]\n\n"
                    "### 💡 Final Recommendation\n"
                    "- [Professional concluding advice for the traveler]"
                )
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"I am from {origin_country}. I want to travel to {destination} ({specific_city}). Analyze safety."}
                ]
                
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "search_official_advisories",
                            "description": "Searches for official government travel warnings using advanced AI search.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "search_query": {
                                        "type": "string",
                                        "description": "Targeted search query (e.g., 'Ministerstwo Spraw Zagranicznych ostrzeżenia dla podróżujących Iran')."
                                    }
                                },
                                "required": ["search_query"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "search_current_events",
                            "description": "Searches recent news articles for safety information.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "search_query": {
                                        "type": "string",
                                        "description": "Search query for news (e.g., 'Iran protests safety current situation')."
                                    }
                                },
                                "required": ["search_query"]
                            }
                        }
                    }
                ]

                # ReAct Loop
                for _ in range(6):
                    response = client.chat.completions.create(
                        model=MODEL, messages=messages, tools=tools, tool_choice="auto", temperature=0.1
                    )
                    msg = response.choices[0].message
                    if msg.tool_calls:
                        messages.append(msg.model_dump(exclude_unset=True))
                        for tool in msg.tool_calls:
                            args = json.loads(tool.function.arguments)
                            if tool.function.name == "search_official_advisories":
                                res = search_official_advisories(args.get("search_query", ""))
                            else:
                                res = search_current_events(args.get("search_query", ""))
                            messages.append({"role": "tool", "tool_call_id": tool.id, "name": tool.function.name, "content": res})
                    else:
                        st.success("Analysis Complete!")
                        st.markdown(msg.content)
                        break
            except Exception as e:
                st.error(f"An error occurred: {e}")

st.markdown("---")
st.caption("Disclaimer: This tool provides autonomous agent-generated summaries. Always verify with official government sources before traveling.")