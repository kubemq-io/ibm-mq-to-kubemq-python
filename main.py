import os

os.environ.setdefault("MQ_FILE_PATH", "C:/Program Files (x86)/IBM/WebSphere MQ")
import pymqi

from typing import Optional


class MQMessageConsumer:
    def __init__(
        self,
        host: str,
        port: int,
        channel: str,
        queue_manager: str,
        queue_name: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize MQ connection parameters

        Args:
            host: MQ server hostname
            port: MQ listener port
            channel: MQ channel name
            queue_manager: Queue manager name
            queue_name: Queue name to consume from
            username: Optional username for authentication
            password: Optional password for authentication
        """
        self.host = host
        self.port = port
        self.channel = channel
        self.queue_manager = queue_manager
        self.queue_name = queue_name
        self.username = username
        self.password = password
        self.conn_info = "%s(%s)" % (host, port)

    def connect(self) -> None:
        """Establish connection to MQ"""
        try:
            # Set up authentication if credentials provided
            if self.username and self.password:
                self.credentials = {"user": self.username, "password": self.password}
            else:
                self.credentials = {}

            print(
                f"Connecting to queue manager: {self.queue_manager} in {self.conn_info}"
            )
            self.qmgr = pymqi.connect(
                self.queue_manager, self.channel, self.conn_info, **self.credentials
            )
        except Exception as e:
            print(f"Error connecting to MQ: {str(e)}")
            return
        try:
            print("open queue for reading")
            self.queue = pymqi.Queue(self.qmgr, self.queue_name)
            print(f"Successfully connected to queue: {self.queue_name}")

        except Exception as e:
            print(f"Error connecting to MQ: {str(e)}")

    def get_message(self, wait_interval: int = 5) -> Optional[str]:
        """
        Get a single message from the queue

        Args:
            wait_interval: Time to wait for message in seconds

        Returns:
            Message content as string if available, None if no message
        """
        try:
            # Set up get message options
            gmo = pymqi.GMO()
            gmo.Options = pymqi.CMQC.MQGMO_WAIT | pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING
            gmo.WaitInterval = wait_interval * 1000  # Convert to milliseconds

            # Get message
            message = self.queue.get(None, gmo)
            return message.decode()

        except pymqi.MQMIError as e:
            if (
                e.comp == pymqi.CMQC.MQCC_FAILED
                and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE
            ):
                return None
            else:
                print(f"Error getting message: {e}")
                raise

    def close(self) -> None:
        """Close queue and disconnect from queue manager"""
        try:
            self.queue.close()
            self.qmgr.disconnect()
            print("Successfully disconnected from MQ")
        except Exception as e:
            print(f"Error closing connections: {e}")
            raise


def main():
    # # Connection parameters - replace with your values
    # config = {
    #     'host': '84.200.100.229',
    #     'port': 32238,
    #     'channel': 'DEV.APP.SVRCONN',
    #     'queue_manager': 'secureapphelm',
    #     'queue_name': 'DEV.QUEUE.1',
    #     'username': 'admin',  # Optional
    #     'password': 'Passw0rd'   # Optional
    # }
    #
    # # Create consumer instance
    # consumer = MQMessageConsumer(**config)
    #
    # try:
    #     # Connect to MQ
    #     consumer.connect()
    #
    #     # # Process messages in a loop
    #     # print("Starting to consume messages...")
    #     # while True:
    #     #     message = consumer.get_message()
    #     #     if message:
    #     #         print(f"Received message: {message}")
    #     #     time.sleep(1)  # Small delay between polls
    #
    # except KeyboardInterrupt:
    #     print("\nStopping message consumer...")
    # finally:
    #     consumer.close()
    queue_manager = "QM1"
    channel = "DEV.APP.SVRCONN"
    host = "localhost"
    port = "1414"
    conn_info = "%s(%s)" % (host, port)

    user = "app"
    password = "passw0rd"
    print(f"Connecting to queue manager: {queue_manager} in {conn_info}")
    qmgr = pymqi.connect(queue_manager, channel, conn_info, user, password)
    print("Successfully connected to queue manager")
    qmgr.disconnect()

    queue_manager = "secureapphelm"
    channel = "SECUREAPP.CHANNEL"
    host = "84.200.100.229"
    port = "32384"
    conn_info = "%s(%s)" % (host, port)

    user = "admin"
    password = "Passw0rd"
    try:
        print(f"Connecting to queue manager: {queue_manager} in {conn_info}")
        qmgr = pymqi.connect(queue_manager, channel, conn_info, user, password)
        print("Successfully connected to queue manager")
        qmgr.disconnect()
    except Exception as e:
        print(f"Error connecting to MQ: {str(e)}")
        return


if __name__ == "__main__":
    main()
