import asyncio
import time
import logging
from typing import List, Set
from .http_probe import probe_host
from .models import upsert_service, get_known_ports

logger = logging.getLogger("localdeck.discovery")

DEFAULT_PORTS = [80,443,3000,3001,3002,3003,3004,3005,3006,3007,3008,3009,3010,4000,4001,4002,4003,4004,4005,8080,8081,8443,8888,9000,9090]

class Scanner:
    def __init__(self, addresses=("127.0.0.1", "::1"), interval=30, timeout=1.5, concurrency=100):
        self.addresses = addresses
        self.interval = interval
        self.timeout = timeout
        self._running = True
        self._semaphore = asyncio.Semaphore(concurrency)

    async def run_background(self):
        while True:
            try:
                await self.scan_once()
            except Exception as e:
                logger.exception("scan failed: %s", e)
            await asyncio.sleep(self.interval)

    async def scan_once(self):
        # assemble ports: defaults + known
        known = get_known_ports()
        ports = list(dict.fromkeys(DEFAULT_PORTS + known))
        tasks = []
        for addr in self.addresses:
            for port in ports:
                tasks.append(self._probe(addr, port))
        # run with limited concurrency
        await asyncio.gather(*tasks)

    async def _probe(self, addr: str, port: int):
        async with self._semaphore:
            try:
                result = await probe_host(addr, port, timeout=self.timeout)
                if result is not None:
                    # result is dict with metadata
                    upsert_service(result)
            except Exception:
                logger.debug("probe failed %s:%d", addr, port, exc_info=True)
