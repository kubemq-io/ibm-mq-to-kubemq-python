from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    host_name: str = Field(default=None, description="Hostname of the IBM MQ server")
    port_number: int = Field(default=None, ge=1, le=65535, description="Port number")
    queue_manager: str = Field(default=None, description="Queue manager name")
    channel_name: str = Field(default=None, description="Channel name")
    queue_name: str = Field(default=None, description="Queue name")
    username: str = Field(default=None, description="Username")
    password: Optional[str] = Field(default=None, description="Password")
    poll_interval_ms: int = Field(
        default=100, ge=1, description="Poll interval in milliseconds"
    )

    @property
    def connection_string(self):
        return "%s(%s)" % (self.host_name, self.port_number)
