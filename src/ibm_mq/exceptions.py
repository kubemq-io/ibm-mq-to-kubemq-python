from __future__ import annotations
class IBMMQConnectionError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
