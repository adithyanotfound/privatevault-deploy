import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

# Optional dependency, used when execute is called
try:
    from google import genai
except ImportError:
    genai = None

AuditHook = Callable[[str, Dict[str, Any]], None]


@dataclass
class ConnectorConfig:
    timeout_seconds: int
    max_retries: int
    model: str


class VaultAuthProvider:
    def __init__(self, env_key: str = "GEMINI_API_KEY"):
        self.env_key = env_key

    def get_credentials(self) -> Dict[str, str]:
        token = os.getenv(self.env_key)
        if not token:
            raise RuntimeError("GEMINI_API_KEY_MISSING")
        return {"api_key": token}


class GeminiConnector:
    id = "pv.ai.gemini"
    domain = "ai"
    version = "1.0.0"

    def __init__(
        self,
        config: Optional[ConnectorConfig] = None,
        auth_provider: Optional[VaultAuthProvider] = None,
        audit_hook: Optional[AuditHook] = None,
    ):
        self.config = config or self._load_config()
        self.auth_provider = auth_provider or VaultAuthProvider()
        self.audit_hook = audit_hook

    def capabilities(self):
        return ["model_invoke"]

    def validate(self, context: Dict[str, Any], action: str) -> None:
        if not context.get("tenant_id"):
            raise ValueError("TENANT_REQUIRED")
        if not context.get("actor_id"):
            raise ValueError("ACTOR_REQUIRED")
        if action not in self.capabilities():
            raise ValueError("ACTION_NOT_SUPPORTED")

    def execute(self, context: Dict[str, Any], action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.validate(context, action)
        self._audit("request", {"action": action, "tenant_id": context.get("tenant_id")})

        if not context.get("quorum"):
            self._audit("error", {"error": "QUORUM_REQUIRED"})
            raise RuntimeError("QUORUM_REQUIRED")

        credentials = self.auth_provider.get_credentials()
        
        if genai is None:
            self._audit("error", {"error": "google-genai not installed"})
            raise RuntimeError("google-genai library is required for GeminiConnector")

        client = genai.Client(api_key=credentials["api_key"])
        model = payload.get("model", self.config.model)
        
        content = payload.get("messages", [])
        if isinstance(content, list):
            prompt = "\n".join([str(m.get("content", "")) for m in content])
        else:
            prompt = str(content)
            
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            result = {"text": response.text}
            self._audit("execution", {"status": "ok"})
            return result
        except Exception as exc:
            self._audit("error", {"error": str(exc)})
            raise exc

    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "connector": self.id}

    def _audit(self, event: str, payload: Dict[str, Any]) -> None:
        if self.audit_hook:
            self.audit_hook(event, payload)

    @staticmethod
    def _load_config() -> ConnectorConfig:
        defaults_path = os.path.join(
            os.path.dirname(__file__), "config", "gemini.defaults.json"
        )
        if os.path.exists(defaults_path):
            with open(defaults_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return ConnectorConfig(
                timeout_seconds=int(raw.get("timeout_seconds", 30)),
                max_retries=int(raw.get("max_retries", 3)),
                model=raw.get("model", "gemini-3-flash-preview"),
            )
        else:
            return ConnectorConfig(
                timeout_seconds=30,
                max_retries=3,
                model="gemini-3-flash-preview"
            )
