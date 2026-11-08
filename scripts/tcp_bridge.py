"""Bounded TCP relay for the private load lab; never logs HTTP payloads."""
import argparse
import asyncio
import ipaddress
import json


class Bridge:
    def __init__(self, target_host, target_port, allowed_peers, *, limit=200, timeout=90):
        self.target = (target_host, target_port)
        self.allowed = frozenset(ipaddress.ip_address(value) for value in allowed_peers)
        self.limit = limit
        self.timeout = timeout
        self.active = set()
        self.stats = {"accepted": 0, "rejected": 0, "connection_errors": 0}

    @staticmethod
    async def copy(reader, writer):
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
        if writer.can_write_eof():
            writer.write_eof()
            await writer.drain()

    @staticmethod
    async def close_writer(writer):
        if writer is None:
            return
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), 2)
        except (TimeoutError, ConnectionError, OSError):
            pass

    async def handle(self, reader, writer):
        peer = writer.get_extra_info("peername")
        if not peer or ipaddress.ip_address(peer[0]) not in self.allowed or len(self.active) >= self.limit:
            self.stats["rejected"] += 1
            await self.close_writer(writer)
            return
        task = asyncio.current_task()
        self.active.add(task)
        self.stats["accepted"] += 1
        upstream = None
        pumps = []
        try:
            source, upstream = await asyncio.wait_for(asyncio.open_connection(*self.target), 10)
            pumps = [asyncio.create_task(self.copy(reader, upstream)),
                     asyncio.create_task(self.copy(source, writer))]
            await asyncio.wait_for(asyncio.gather(*pumps), self.timeout)
        except (TimeoutError, ConnectionError, OSError):
            self.stats["connection_errors"] += 1
        finally:
            for pump in pumps:
                if not pump.done():
                    pump.cancel()
            await asyncio.gather(*pumps, return_exceptions=True)
            await self.close_writer(upstream)
            await self.close_writer(writer)
            self.active.discard(task)

    async def close(self):
        tasks = list(self.active)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def serve(args):
    bridge = Bridge(args.target_host, args.target_port, args.allow_peer,
                    limit=args.max_connections, timeout=args.connection_timeout)
    server = await asyncio.start_server(bridge.handle, args.listen_host, args.listen_port)
    print(json.dumps({"status": "ready", "listen_host": args.listen_host,
                      "listen_port": args.listen_port, "lifetime_seconds": args.lifetime}), flush=True)
    try:
        async with server:
            await asyncio.sleep(args.lifetime)
    finally:
        await bridge.close()
        print(json.dumps({"status": "stopped", **bridge.stats}), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--target-host", required=True)
    parser.add_argument("--target-port", type=int, required=True)
    parser.add_argument("--allow-peer", action="append", required=True)
    parser.add_argument("--max-connections", type=int, default=200)
    parser.add_argument("--connection-timeout", type=int, default=90)
    parser.add_argument("--lifetime", type=int, default=10800)
    args = parser.parse_args(argv)
    try:
        addresses = [ipaddress.ip_address(v) for v in
                     [args.listen_host, args.target_host, *args.allow_peer]]
    except ValueError:
        parser.error("Use explicit numeric interface, target and peer addresses")
    if any(address.is_unspecified or not (address.is_loopback or address.is_private) for address in addresses):
        parser.error("Only explicit loopback/private addresses are permitted")
    if not (1024 <= args.listen_port <= 65535 and 1 <= args.target_port <= 65535
            and 1 <= args.max_connections <= 1000 and 1 <= args.connection_timeout <= 300
            and 1 <= args.lifetime <= 14400):
        parser.error("Invalid ports, connection limit, timeout or bounded lifetime")
    asyncio.run(serve(args))


if __name__ == "__main__":
    main()
