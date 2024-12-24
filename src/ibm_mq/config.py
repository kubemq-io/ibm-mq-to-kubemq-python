from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Config(BaseModel):
    binding_name: Optional[str] = Field(default=None, description="Binding name")
    binding_type: Optional[str] = Field(default=None, description="Binding type")
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
    ssl: bool = Field(default=False, description="Use SSL")
    ssl_cipher_spec: Optional[str] = Field(
        default=None, description="SSL cipher specification"
    )
    key_repo_location: Optional[str] = Field(
        default=None, description="Key repository location"
    )

    @property
    def connection_string(self):
        return "%s(%s)" % (self.host_name, self.port_number)

    @model_validator(mode="after")
    def validate_ssl_fields(self):
        if self.ssl:
            if not self.ssl_cipher_spec:
                raise ValueError("ssl_cipher_spec is required when ssl is True")
            if not self.key_repo_location:
                raise ValueError("key_repo_location is required when ssl is True")
        return self
