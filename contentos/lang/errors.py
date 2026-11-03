class LangError(Exception):
    """Actionable language/model failure. `code` is stable for tests and logs; `hint` says how to fix it."""
    def __init__(self, message, code="lang_error", hint=""):
        super().__init__(message)
        self.code, self.hint = code, hint

    def __str__(self):
        return f"[{self.code}] {super().__str__()}" + (f" -- {self.hint}" if self.hint else "")
