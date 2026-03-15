import json
import os
from datetime import datetime

class AuditLogger:
    def __init__(self, log_file: str = "audit.log"):
        self.log_file = log_file

    def log_tool_call(self, tool_name: str, arguments: str, passed: bool, reason: str):
        """
        Appends a JSON-Lines record of the intercepted tool call.
        """
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "tool_interception",
            "tool": tool_name,
            "arguments": arguments,
            "security_passed": passed,
            "reason": reason
        }
        
        # Append to file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
