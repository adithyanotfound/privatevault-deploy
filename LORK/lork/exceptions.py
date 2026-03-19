"""
lork/exceptions.py
==================
All LORK-specific exceptions.
"""


class LorkError(Exception):

    code: str = "LORK_ERROR"
    http_status: int = 500

    def __init__(self, message: str, **context):
        super().__init__(message)
        self.message = message
        self.context = context

    def to_dict(self) -> dict:
        return {
            "error": self.code,
            "message": self.message,
            **self.context,
        }


class AgentNotFoundError(LorkError):
    code = "LORK_AGENT_NOT_FOUND"
    http_status = 404


class TaskNotFoundError(LorkError):
    code = "LORK_TASK_NOT_FOUND"
    http_status = 404


class PolicyNotFoundError(LorkError):
    code = "LORK_POLICY_NOT_FOUND"
    http_status = 404


class TenantNotFoundError(LorkError):
    code = "LORK_TENANT_NOT_FOUND"
    http_status = 404


class RunNotFoundError(LorkError):
    code = "LORK_RUN_NOT_FOUND"
    http_status = 404


class AgentAlreadyExistsError(LorkError):
    code = "LORK_AGENT_ALREADY_EXISTS"
    http_status = 409


class TenantAlreadyExistsError(LorkError):
    code = "LORK_TENANT_ALREADY_EXISTS"
    http_status = 409


class PolicyDeniedError(LorkError):
    code = "LORK_POLICY_DENIED"
    http_status = 403


class ApprovalRequiredError(LorkError):
    code = "LORK_APPROVAL_REQUIRED"
    http_status = 403


class AgentSuspendedError(LorkError):
    code = "LORK_AGENT_SUSPENDED"
    http_status = 403


class InsufficientPermissionsError(LorkError):
    code = "LORK_INSUFFICIENT_PERMISSIONS"
    http_status = 403


class InvalidAgentConfigError(LorkError):
    code = "LORK_INVALID_AGENT_CONFIG"
    http_status = 422


class InvalidPolicyError(LorkError):
    code = "LORK_INVALID_POLICY"
    http_status = 422


class InvalidTaskInputError(LorkError):
    code = "LORK_INVALID_TASK_INPUT"
    http_status = 422


class RuntimeExecutionError(LorkError):
    code = "LORK_RUNTIME_EXECUTION_ERROR"
    http_status = 500


class LLMCallError(LorkError):
    code = "LORK_LLM_CALL_ERROR"
    http_status = 502


class ToolCallError(LorkError):
    code = "LORK_TOOL_CALL_ERROR"
    http_status = 502


class LLMQuotaExceededError(LorkError):
    code = "LORK_LLM_QUOTA_EXCEEDED"
    http_status = 429


class SchedulerOverloadedError(LorkError):
    code = "LORK_SCHEDULER_OVERLOADED"
    http_status = 503


class TaskDeadlineExceededError(LorkError):
    code = "LORK_TASK_DEADLINE_EXCEEDED"
    http_status = 408


class StorageError(LorkError):
    code = "LORK_STORAGE_ERROR"
    http_status = 500


class StorageConnectionError(StorageError):
    code = "LORK_STORAGE_CONNECTION_ERROR"
    http_status = 503
