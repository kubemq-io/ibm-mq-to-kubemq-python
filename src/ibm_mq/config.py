from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    host_name: str = Field(default=None, description="Hostname of the IBM MQ server")
    port_number: int = Field(default=None, description="Port of the IBM MQ server")
    queue_manager: str = Field(default=None, description="Queue manager name")
    channel_name: str = Field(default=None, description="Channel name")
    queue_name: str = Field(default=None, description="Queue name")
    username: str = Field(default=None, description="Username")
    password: Optional[str] = Field(default=None, description="Password")

    @property
    def connection_string(self):
        return "%s(%s)" % (self.host_name, self.port_number)
