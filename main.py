import logging
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from proxy import forward_request
from rules_engine import RulesEngine
from audit_logger import AuditLogger
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

app = FastAPI(title="Agent-First Gateway MVP")

# Mount Static UI
app.mount("/static", StaticFiles(directory="static"), name="static")

rules_engine = RulesEngine()
audit_logger = AuditLogger(log_file="audit.log")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/api/logs")
async def get_logs():
    """Returns the parsed audit logs, latest first."""
    if not os.path.exists("audit.log"):
        return {"logs": []}
    
    logs = []
    try:
        with open("audit.log", "r") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {"logs": [], "error": str(e)}
        
    return {"logs": logs[::-1]} # Return newest first

@app.post("/v1/messages")
async def anthropic_messages(request: Request):
    """
    Intercepts the standard Anthropic /v1/messages endpoint.
    """
    try:
        body = await request.json()
        logger.info(f"Incoming request for model: {body.get('model', 'unknown')}")
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": {"message": "Invalid JSON"}})

    # Forward the request to the upstream provider (Anthropic)
    response_data, status_code = await forward_request(body, "/v1/messages")

    if status_code != 200:
        return JSONResponse(status_code=status_code, content=response_data)

    # If it's a stream, we currently don't intercept tools (MVP limitation)
    if body.get("stream"):
        logger.warning("Streaming tool interception is not yet supported in MVP.")
        return response_data

    # Parse and Intercept Tool Calls (Anthropic format)
    # The response is a list of 'content' blocks. Some are text, some are tool_use
    if "content" in response_data:
        # We need to create a new content array to potentially filter out blocked tools
        new_content = []
        is_blocked = False
        block_reasons = []

        for block in response_data["content"]:
            if block.get("type") == "tool_use":
                tool_name = block.get("name")
                # Anthropic tool args are already a dict, unlike OpenAI which is stringified JSON
                tool_args_dict = block.get("input", {})
                tool_args_str = json.dumps(tool_args_dict)
                
                logger.info(f"Intercepted tool call: {tool_name}")
                
                # Run the rules engine (requires string input, so we stringify it)
                result = rules_engine.evaluate(tool_name, tool_args_str)
                
                # Log the outcome
                audit_logger.log_tool_call(
                    tool_name=tool_name,
                    arguments=tool_args_str,
                    passed=result.passed,
                    reason=result.reason
                )
                
                if not result.passed:
                    logger.warning(f"BLOCKED tool call {tool_name}: {result.reason}")
                    is_blocked = True
                    block_reasons.append(f"Tool '{tool_name}' denied: {result.reason}")
                else:
                    new_content.append(block) # Keep the safe tool call
            else:
                # Text blocks pass through natively
                new_content.append(block)
                
        if is_blocked:
            # Synthetic injection: We rewrite the LLM's response to simulate a failure
            # We add a text block explaining the security block
            error_message = "[GATEWAY SECURITY BLOCK]: " + " | ".join(block_reasons)
            new_content.append({
                "type": "text",
                "text": error_message
            })
            # Override the finish reason so the agent handles it like a stop
            response_data["stop_reason"] = "end_turn"
            
        response_data["content"] = new_content
    
    return JSONResponse(status_code=status_code, content=response_data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
