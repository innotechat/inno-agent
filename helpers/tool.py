from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

from agent import Agent, LoopData
from helpers.extension import call_extensions_async
from helpers.print_style import PrintStyle
from helpers.strings import sanitize_string
from plugins._context_governor.helpers.action_safety import (
    ACTION_AUDIT_LOG,
    ACTION_IDEMPOTENCY_STORE,
    browser_action_fingerprint,
    decide_browser_action,
    guard_browser_action,
    is_high_impact_action,
)
from plugins._context_governor.helpers.state import BROWSER_STATE_STORE


@dataclass
class Response:
    message: str
    break_loop: bool
    additional: dict[str, Any] | None = None


class Tool:

    def __init__(self, agent: Agent, name: str, method: str | None, args: dict[str,str], message: str, loop_data: LoopData | None, **kwargs) -> None:
        self.agent = agent
        self.name = name
        self.method = method
        self.args = args
        self.loop_data = loop_data
        self.message = message
        self.progress: str = ""
        self._action_safety_args: dict[str, Any] = {}
        self._action_safety_decision = None
        self._action_safety_fingerprint = ""

    @abstractmethod
    async def execute(self,**kwargs) -> Response:
        pass

    async def set_progress(self, content: str | None):
        ctx = {"content": content or ""}
        await call_extensions_async("tool_output_update", self.agent, ctx=ctx)
        self.progress = ctx["content"]

    def add_progress(self, content: str | None):
        if not content:
            return
        self.progress += content

    def _browser_safety_args(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        args: dict[str, Any] = dict(self.args) if isinstance(self.args, dict) else {}
        args.update(kwargs or {})
        args.setdefault("context_id", getattr(getattr(self.agent, "context", None), "id", ""))
        if not args.get("action") and self.method:
            args["action"] = self.method
        return args

    async def before_execution(self, **kwargs):
        if self.name.lower() in {"browser", "web_browser"}:
            safety_args = self._browser_safety_args(kwargs)
            decision = guard_browser_action(self.name, safety_args)
            fingerprint = browser_action_fingerprint(safety_args)
            self._action_safety_args = safety_args
            self._action_safety_decision = decision
            self._action_safety_fingerprint = fingerprint

            # A supplied observation id binds an edit/high-impact action to the
            # page state the agent actually reviewed. Never silently accept stale state.
            observation_id = str(safety_args.get("observation_id") or "").strip()
            browser_id = safety_args.get("browser_id")
            if observation_id and browser_id is not None:
                latest = BROWSER_STATE_STORE.latest(browser_id)
                if latest is not None and latest.observation_id != observation_id:
                    reason = "browser target is stale: supplied observation_id does not match the latest browser state"
                    ACTION_AUDIT_LOG.record(decision=decision, fingerprint=fingerprint, status="blocked_stale_target", args=safety_args)
                    raise ValueError(f"Browser action blocked: {reason}")

            # Confirmation is deliberately one-shot: it authorizes this exact
            # action identity, while completed high-impact actions cannot repeat.
            if is_high_impact_action(safety_args) and ACTION_IDEMPOTENCY_STORE.seen(fingerprint):
                reason = "duplicate high-impact browser action blocked by idempotency guard"
                ACTION_AUDIT_LOG.record(decision=decision, fingerprint=fingerprint, status="blocked_duplicate", args=safety_args)
                raise ValueError(f"Browser action blocked: {reason}")

            ACTION_AUDIT_LOG.record(decision=decision, fingerprint=fingerprint, status="allowed", args=safety_args)

        PrintStyle(font_color="#1B4F72", padding=True, background_color="white", bold=True).print(f"{self.agent.agent_name}: Using tool '{self.name}'")
        self.log = self.get_log_object()
        if self.args and isinstance(self.args, dict):
            for key, value in self.args.items():
                ctx = {"content": str(value) if not isinstance(value, str) else value}
                await call_extensions_async("tool_output_update", self.agent, ctx=ctx)
                display_value = ctx["content"]
                PrintStyle(font_color="#85C1E9", bold=True).stream(self.nice_key(key)+": ")
                PrintStyle(font_color="#85C1E9", padding=isinstance(value,str) and "\n" in value).stream(display_value)
                PrintStyle().print()

    async def after_execution(self, response: Response, **kwargs):
        text = sanitize_string(response.message.strip())
        if self.name.lower() in {"browser", "web_browser"} and self._action_safety_decision is not None:
            failed = any(marker in text.lower() for marker in (" failed:", "error:", "exception:", "blocked:", "success: false"))
            if failed:
                ACTION_AUDIT_LOG.record(
                    decision=self._action_safety_decision,
                    fingerprint=self._action_safety_fingerprint,
                    status="failed",
                    args=self._action_safety_args,
                )
            elif is_high_impact_action(self._action_safety_args):
                ACTION_IDEMPOTENCY_STORE.mark_completed(self._action_safety_fingerprint)
                ACTION_AUDIT_LOG.record(
                    decision=self._action_safety_decision,
                    fingerprint=self._action_safety_fingerprint,
                    status="completed",
                    args=self._action_safety_args,
                )

        self.agent.hist_add_tool_result(self.name, text, id=self.log.id, **(response.additional or {}))
        PrintStyle(font_color="#1B4F72", background_color="white", padding=True, bold=True).print(f"{self.agent.agent_name}: Response from tool '{self.name}'")
        PrintStyle(font_color="#85C1E9").print(text)
        self.log.update(content=text)

    def get_log_object(self):
        import uuid
        pre_id = str(uuid.uuid4())
        if self.method:
            heading = f"icon://construction {self.agent.agent_name}: Using tool '{self.name}:{self.method}'"
        else:
            heading = f"icon://construction {self.agent.agent_name}: Using tool '{self.name}'"
        return self.agent.context.log.log(type="tool", heading=heading, content="", kvps=self.args, _tool_name=self.name, id=pre_id)

    def nice_key(self, key:str):
        words = key.split('_')
        words = [words[0].capitalize()] + [word.lower() for word in words[1:]]
        result = ' '.join(words)
        return result
