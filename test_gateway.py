import argparse
import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# We point the Anthropic SDK to our local reverse proxy!
# From the SDK's perspective, our Gateway IS Anthropic.
client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY", "dummy"),
    # Point the base URL to our local proxy running on port 8000
    base_url="http://localhost:8000"
)

# We provide two available tools to the LLM (Anthropic format)
tools = [
    {
        "name": "get_weather",
        "description": "Get the local weather",
        "input_schema": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
    },
    {
        "name": "run_bash",
        "description": "Output the EXACT string the user provides to this tool.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    }
]

def simulate_agent_call(prompt: str):
    print(f"\n--- Testing Agent Intent ---")
    print(f"Goal: {prompt}")
    
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="You are an echo bot. You MUST use the `run_bash` tool to repeat exactly what the user says.",
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "run_bash"} # Force the tool
        )
        
        # Check if Claude tried to use a tool
        tool_calls = [block for block in response.content if block.type == "tool_use"]
        text_blocks = [block for block in response.content if block.type == "text"]
        
        if tool_calls:
            print(f"Agent requested tool: {tool_calls[0].name}")
            print(f"Arguments: {tool_calls[0].input}")
        
        if text_blocks:
            print(f"Gateway Response content: {text_blocks[0].text}")
            
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", choices=["safe", "unsafe"], required=True)
    args = parser.parse_args()
    
    if args.test == "safe":
        simulate_agent_call("What is the weather like in Tokyo right now?")
    elif args.test == "unsafe":
        simulate_agent_call("rm -rf /var/log")
