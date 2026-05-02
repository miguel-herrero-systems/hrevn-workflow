class WorkflowError(Exception):
    """Base error for hrevn-workflow."""


class StepStateError(WorkflowError):
    """Raised when a step is used in an invalid way."""


class WorkflowIntegrityError(WorkflowError):
    """Raised when workflow state or outputs fail integrity checks."""
