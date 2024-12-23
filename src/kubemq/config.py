import socket
from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    binding_name: Optional[str] = Field(default=None, description="Binding name")
    binding_type: Optional[str] = Field(default=None, description="Binding type")
    address: str = Field(default=None, description="Address of the Kubemq server")
    queue_name: str = Field(default=None, description="Queue name")
    client_id: Optional[str] = Field(
        default=lambda: socket.gethostname(), description="Client ID"
    )
    auth_token: Optional[str] = Field(default=None, description="Authentication token")

    tls: Optional[bool] = Field(default=False, description="Use TLS")
    tls_cert_file: Optional[str] = Field(
        default=None, description="TLS certificate file"
    )
    tls_key_file: Optional[str] = Field(
        default=None, description="TLS certificate file"
    )
    tls_ca_file: Optional[str] = Field(default=None, description="TLS certificate file")
    poll_interval_seconds: int = Field(
        default=1, ge=1, description="Poll interval in seconds"
    )
