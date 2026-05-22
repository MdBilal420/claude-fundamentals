import json
import anthropic

from dotenv import load_dotenv
import os

load_dotenv()
my_api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(
    api_key=my_api_key
)

tools = [
    {
        "name": "create_calendar_event",
        "description": "Create a calendar event with attendees and optional recurrence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start": {"type": "string", "format": "date-time"},
                "end": {"type": "string", "format": "date-time"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string", "format": "email"},
                },
                "recurrence": {
                    "type": "object",
                    "properties": {
                        "frequency": {"enum": ["daily", "weekly", "monthly"]},
                        "count": {"type": "integer", "minimum": 1},
                    },
                },
            },
            "required": ["title", "start", "end"],
        },
    }
]

def run_tool(tool_name, tool_input):
    if tool_name == "create_calendar_event":
        return {"event_id": "evt_123", "status": "created", "title": tool_input["title"]}
    else:
        raise ValueError(f"Tool {tool_name} not found")

messages = [
    {
        "role": "user",
        "content": "Schedule a weekly team standup every Monday at 9am for the next 4 weeks. Invite the whole team: alice@example.com, bob@example.com, carol@example.com.",
    }
]

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    tools=tools,
    tool_choice={"type": "auto", "disable_parallel_tool_use": True},
    messages=messages
)


while response.stop_reason == "tool_use":
    tool_use = next(block for block in response.content if block.type == "tool_use")
    result = run_tool(tool_use.name, tool_use.input)

    messages.append({
        "role" : "assistant",
        "content" : response.content,
    })

    messages.append({
        "role" : "user",
        "content" : [
            {
                "type" : "tool_result",
                "tool_use_id" : tool_use.id,
                "content" : json.dumps(result),
            }
        ]
    })

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        tools=tools,
        tool_choice={"type": "auto", "disable_parallel_tool_use": True},
        messages=messages
    )

answer = next(block for block in response.content if block.type == "text")

print("Answer:", answer.text)
