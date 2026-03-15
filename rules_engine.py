import json
import re
from typing import Dict, Any, List, Union

class RuleResult:
    def __init__(self, passed: bool, reason: str = ""):
        self.passed = passed
        self.reason = reason

class RulesEngine:
    def __init__(self):
        # We start with basic regex rules for MVP
        self.dangerous_sql_keywords = re.compile(
            r'\b(DROP|DELETE|TRUNCATE|ALTER|UPDATE)\b', re.IGNORECASE
        )
        self.blocked_bash_commands = [
            "rm -rf", "sudo", "mkfs", "chown", "chmod", 
            "/etc/passwd", "/root", "wget", "curl"
        ]

    def evaluate(self, tool_name: str, tool_args: Union[str, Dict]) -> RuleResult:
        """
        Evaluates a tool call to determine if it violates security policies.
        Returns a RuleResult (passed=True/False, reason=...)
        """
        if isinstance(tool_args, str):
            try:
                args_dict = json.loads(tool_args)
            except json.JSONDecodeError:
                return RuleResult(False, "Failed to parse tool arguments JSON")
        else:
            args_dict = tool_args

        # 1. Evaluate generic bash/shell execution tools
        if tool_name in ["run_bash", "execute_command", "shell"]:
            command = args_dict.get("command", "").lower()
            for blocked in self.blocked_bash_commands:
                if blocked in command:
                    return RuleResult(False, f"Blocked bash command detected: {blocked}")

        # 2. Evaluate SQL execution tools
        if tool_name in ["run_sql", "execute_query", "db_query"]:
            query = args_dict.get("query", "")
            if self.dangerous_sql_keywords.search(query):
                return RuleResult(False, "Blocked destructive SQL keyword (DROP/DELETE/TRUNCATE/ALTER/UPDATE)")

        # 3. Future evaluation (e.g. SLM intent check) would go here

        return RuleResult(True, "Passed all rules")
