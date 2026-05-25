import json
import anthropic
from tavily import TavilyClient

from dotenv import load_dotenv
import os

load_dotenv()
my_api_key = os.getenv("ANTHROPIC_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")
MAX_TAVILY_SEARCHES = int(os.getenv("TAVILY_MAX_SEARCHES", "2"))

tavily_client = TavilyClient(api_key=tavily_api_key)
_tavily_search_count = 0
client = anthropic.Anthropic(
    api_key=my_api_key
)

tools = [
    {
        "name": "web_search",
        "description": (
            "Search the web for recent information using Tavily. "
            f"Use at most {MAX_TAVILY_SEARCHES} searches per run; combine queries when possible."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a local file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path of the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write into the file"
                }
            },
            "required": ["path", "content"]
        }
    }
]

def run_tool(tool_name, tool_input):
    if tool_name == "web_search":
        return web_search(tool_input["query"])
    elif tool_name == "write_file":
        return write_file(tool_input["path"], tool_input["content"])
    else:
        raise ValueError(f"Tool {tool_name} not found")

def web_search(query):
    global _tavily_search_count
    if _tavily_search_count >= MAX_TAVILY_SEARCHES:
        return {
            "error": (
                f"Tavily search limit reached ({MAX_TAVILY_SEARCHES} per run). "
                "Continue with results you already have."
            ),
            "results": [],
            "answer": None,
        }
    _tavily_search_count += 1
    print(f"[Runtime] Tavily search {_tavily_search_count}/{MAX_TAVILY_SEARCHES}")
    response = tavily_client.search(
        query,
        search_depth="basic",
        max_results=5,
        include_answer=True,
    )
    return {
        "results": response.get("results", []),
        "answer": response.get("answer"),
    }

def write_file(path, content):
    with open(path, "w") as file:
        file.write(content)
    return {
        "content" : "File written successfully",
        "path" : path
    }


messages = [
    {
        "role": "user",
        "content": (
            "Research AI coding agents. Search the web, then write a detailed "
            "report to report.md using write_file, then give me a brief summary."
        ),
    }
]

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8192,
    tools=tools,
    tool_choice={"type": "auto", "disable_parallel_tool_use": True},
    messages=messages,
)

turn = 1
while response.stop_reason == "tool_use":
    print(f"\n--- Turn {turn} (stop_reason: tool_use) ---")
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            print(f"[Claude] Calling {block.name}({json.dumps(block.input)})")
            print(f"[Runtime] Executing {block.name}...")
            result = run_tool(block.name, block.input)
            if block.name == "web_search":
                if result.get("error"):
                    print(f"[Runtime] {result['error']}")
                else:
                    n = len(result.get("results", []))
                    print(f"[Runtime] Tavily returned {n} results")
            elif block.name == "write_file":
                print(f"[Runtime] Wrote {result['path']}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })
    turn += 1

    messages.append({
        "role": "assistant",
        "content": response.content,
    })
    messages.append({
        "role": "user",
        "content": tool_results,
    })

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        tools=tools,
        tool_choice={"type": "auto", "disable_parallel_tool_use": True},
        messages=messages,
    )

print(f"\n--- Final response (stop_reason: {response.stop_reason}) ---")
answer = next(block for block in response.content if block.type == "text")
print("Answer:", answer.text)