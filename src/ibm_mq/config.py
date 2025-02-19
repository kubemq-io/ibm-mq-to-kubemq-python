from typing import Optional

from pydantic import BaseModel, Field, model_validator
import pymqi


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
    message_ccsid: Optional[int] = Field(default=1208, description="CCSID")
    message_format: Optional[str] = Field(default="", description="Message format")
    receiver_mode: Optional[str] = Field("default", description="Receiver mode")
    log_received_messages: bool = Field(
        default=False, description="Log received messages"
    )
    log_sent_messages: bool = Field(default=False, description="Log sent messages")
    sender_mode: Optional[str] = Field("default", description="Sender mode")
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

    def get_md_format(self) -> bytes:
        format_map = {
            "": pymqi.CMQC.MQFMT_NONE,
            "MQADMIN": pymqi.CMQC.MQFMT_ADMIN,
            "MQAMQP": pymqi.CMQC.MQFMT_AMQP,
            "MQCHCOM": pymqi.CMQC.MQFMT_CHANNEL_COMPLETED,
            "MQCICS": pymqi.CMQC.MQFMT_CICS,
            "MQCMD1": pymqi.CMQC.MQFMT_COMMAND_1,
            "MQCMD2": pymqi.CMQC.MQFMT_COMMAND_2,
            "MQDEAD": pymqi.CMQC.MQFMT_DEAD_LETTER_HEADER,
            "MQHDIST": pymqi.CMQC.MQFMT_DIST_HEADER,
            "MQHEPCF": pymqi.CMQC.MQFMT_EVENT,
            "MQEVENT": pymqi.CMQC.MQFMT_EVENT,
            "MQIMS": pymqi.CMQC.MQFMT_IMS,
            "MQIMSVS": pymqi.CMQC.MQFMT_IMS_VAR_STRING,
            "MQHMDE": pymqi.CMQC.MQFMT_MD_EXTENSION,
            "MQPCF": pymqi.CMQC.MQFMT_PCF,
            "MQHREF": pymqi.CMQC.MQFMT_REF_MSG_HEADER,
            "MQHRF": pymqi.CMQC.MQFMT_RF_HEADER,
            "MQHRF2": pymqi.CMQC.MQFMT_RF_HEADER_2,
            "MQSTR": pymqi.CMQC.MQFMT_STRING,
            "MQTRIG": pymqi.CMQC.MQFMT_TRIGGER,
            "MQHWIH": pymqi.CMQC.MQFMT_WORK_INFO_HEADER,
            "MQXMIT": pymqi.CMQC.MQFMT_XMIT_Q_HEADER,
        }
        clean_format = self.message_format.strip().upper()
        return format_map.get(clean_format, pymqi.CMQC.MQFMT_NONE)
