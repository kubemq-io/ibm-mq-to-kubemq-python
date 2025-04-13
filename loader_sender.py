from kubemq.queues import *


async def sender():
    async with Client(
        address="localhost:50000",
    ) as client:

        async def _send():
            while True:
                for i in range(10):
                    send_result = await client.send_queues_message_async(
                        QueueMessage(
                            channel="to_ibm",
                            body=b"message",
                        ),
                    )
                    if send_result.is_error:
                        print(f"Error sending message: {send_result.error}")
                        continue
                    print(f"Queue Message Sent: {send_result}")
                await asyncio.sleep(1)

        task1 = asyncio.create_task(_send())
        tasks = [task1]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(sender())
