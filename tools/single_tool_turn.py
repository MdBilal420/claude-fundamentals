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
        "name" : "create_calendar_event",
        "description" : "Create a calendar event for a given date and time",
        "input_schema" : {
            "type" : "object",
            "properties" : {
                "date" : { "type" : "string" },
            }
        },
        # "required" : ["date", "time"]
    }
]


response =  client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    tools=tools,
    messages=[
        {"role": "user", "content": "Create a calendar event for 22nd May 2026 at 10am"}
    ]
)

tool_use = next(block for block in response.content if block.type == "tool_use")
print(f"Tool: {tool_use.name}")
print(f"Input: {tool_use.input}")

# Execute the tool. In a real system this would call your calendar API.
# Here the result is hardcoded to keep the example self-contained.
result = {"event_id": "evt_123", "status": "created"}

follow_up_response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    tools=tools,
    tool_choice={"type": "auto", "disable_parallel_tool_use": True},
    messages=[
        {
            "role": "user",
            "content": "Schedule a 30-minute sync with alice@example.com and bob@example.com next Monday at 10am.",
        },
        {"role": "assistant", "content": response.content},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(result),
                }
            ],
        },
    ],
)

print(follow_up_response.content[0].text)