from src.bindings.connection import Connection


class Binding:
    def __init__(self, source: Connection, target: Connection):
        self.source = source
        self.target = target

    async def start(self):
        await self.target.start()
        await self.source.start()
        await self.source.poll(self.target.send_message)

    async def stop(self):
        await self.source.stop()
        await self.target.stop()
