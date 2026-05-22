class UsageError(Exception):
    """Raised for invalid local CLI usage or configuration."""


class ApiError(Exception):
    """Raised for ONES API failures."""

    def __init__(self, message, status=None, error_code=None, error_msg=None):
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.error_msg = error_msg
