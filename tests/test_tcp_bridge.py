import asyncio
import unittest
from scripts.tcp_bridge import Bridge


class TCPBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_response_after_client_half_close_is_preserved(self):
        async def backend(reader, writer):
            writer.write((await reader.read()).upper())
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        target = await asyncio.start_server(backend, "127.0.0.1", 0)
        bridge = Bridge("127.0.0.1", target.sockets[0].getsockname()[1], ["127.0.0.1"])
        listener = await asyncio.start_server(bridge.handle, "127.0.0.1", 0)
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", listener.sockets[0].getsockname()[1])
            writer.write(b"private fixture")
            await writer.drain()
            writer.write_eof()
            self.assertEqual(await asyncio.wait_for(reader.read(), 3), b"PRIVATE FIXTURE")
            writer.close()
            await writer.wait_closed()
        finally:
            listener.close()
            target.close()
            await listener.wait_closed()
            await target.wait_closed()
            await bridge.close()

    async def test_unlisted_peer_cannot_reach_backend(self):
        reached = asyncio.Event()

        async def backend(reader, writer):
            reached.set()
            writer.close()
            await writer.wait_closed()

        target = await asyncio.start_server(backend, "127.0.0.1", 0)
        bridge = Bridge("127.0.0.1", target.sockets[0].getsockname()[1], ["127.0.0.2"])
        listener = await asyncio.start_server(bridge.handle, "127.0.0.1", 0)
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", listener.sockets[0].getsockname()[1])
            self.assertEqual(await asyncio.wait_for(reader.read(), 3), b"")
            self.assertFalse(reached.is_set())
            writer.close()
            await writer.wait_closed()
        finally:
            listener.close()
            target.close()
            await listener.wait_closed()
            await target.wait_closed()
            await bridge.close()


if __name__ == "__main__":
    unittest.main()
