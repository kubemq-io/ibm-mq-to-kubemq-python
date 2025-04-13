from kubemq.queues import *


async def example_send_receive():
    async with Client(
        address="localhost:50000",
    ) as client:

        async def _receive():
            while True:
                send_receive_result = await client.receive_queues_messages_async(
                    channel="from_ibm",
                    max_messages=10,
                    wait_timeout_in_seconds=1,
                )
                if send_receive_result.is_error:
                    print(f"Error receiving message: {send_receive_result.error}")
                    await asyncio.sleep(1)
                    continue
                for message in send_receive_result.messages:
                    print(f"Id:{message.id}, Body:{message.body.decode('utf-8')}")
                    message.ack()

        task2 = asyncio.create_task(_receive())
        tasks = [task2]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(example_send_receive())
