"""公开发布防护的单元测试（离线，不调用 LLM）。"""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from starlette.requests import Request

from app.config import settings
from app.services.public_guard import (
    PlanGate,
    SlidingWindowLimiter,
    client_ip,
    is_admin_token,
)


def _make_request(client=("9.9.9.9", 1234), forwarded_for=None, real_ip=None):
    headers = []
    if forwarded_for:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    if real_ip:
        headers.append((b"x-real-ip", real_ip.encode()))
    scope = {"type": "http", "client": client, "headers": headers}
    return Request(scope)


class SlidingWindowLimiterTest(unittest.IsolatedAsyncioTestCase):
    async def test_daily_limit(self):
        limiter = SlidingWindowLimiter(per_day=2, per_minute=0)
        self.assertTrue((await limiter.allow("1.1.1.1"))[0])
        self.assertTrue((await limiter.allow("1.1.1.1"))[0])
        ok, retry_after = await limiter.allow("1.1.1.1")
        self.assertFalse(ok)
        self.assertGreater(retry_after, 0)
        # 不同 IP 互不影响
        self.assertTrue((await limiter.allow("2.2.2.2"))[0])

    async def test_burst_limit(self):
        limiter = SlidingWindowLimiter(per_day=100, per_minute=1)
        self.assertTrue((await limiter.allow("ip"))[0])
        ok, retry_after = await limiter.allow("ip")
        self.assertFalse(ok)
        self.assertLessEqual(retry_after, 60)

    async def test_reset(self):
        limiter = SlidingWindowLimiter(per_day=1, per_minute=0)
        self.assertTrue((await limiter.allow("ip"))[0])
        self.assertFalse((await limiter.allow("ip"))[0])
        limiter.reset()
        self.assertTrue((await limiter.allow("ip"))[0])


class PlanGateTest(unittest.IsolatedAsyncioTestCase):
    async def test_queue_limit(self):
        gate = PlanGate(max_concurrent=1, queue_limit=1)
        self.assertTrue(await gate.admit())  # waiting = 1
        self.assertFalse(await gate.admit())  # 已满

        done = asyncio.Event()

        async def work():
            done.set()
            return "ok"

        task = asyncio.create_task(gate.run(work()))
        await done.wait()
        self.assertEqual(await task, "ok")
        self.assertEqual(gate.waiting, 0)
        self.assertTrue(await gate.admit())

    async def test_serialized_execution(self):
        gate = PlanGate(max_concurrent=1, queue_limit=5)
        order = []

        async def work(index, delay):
            await asyncio.sleep(delay)
            order.append(index)

        await asyncio.gather(
            gate.run(work(1, 0.05)),
            gate.run(work(2, 0.0)),
        )
        self.assertEqual(order, [1, 2])
        self.assertEqual(gate.waiting, 0)


class AdminTokenTest(unittest.TestCase):
    def test_compare(self):
        with patch.object(settings, "admin_token", "s3cret-token"):
            self.assertTrue(is_admin_token("s3cret-token"))
            self.assertFalse(is_admin_token("wrong"))
            self.assertFalse(is_admin_token(None))
            self.assertFalse(is_admin_token(""))

    def test_empty_admin_token_never_passes(self):
        with patch.object(settings, "admin_token", ""):
            self.assertFalse(is_admin_token(""))


class ClientIpTest(unittest.TestCase):
    def test_direct_client_ip(self):
        request = _make_request()
        with patch.object(settings, "trust_proxy", False):
            self.assertEqual(client_ip(request), "9.9.9.9")

    def test_forwarded_for_when_trusted(self):
        request = _make_request(forwarded_for="1.2.3.4, 5.6.7.8")
        with patch.object(settings, "trust_proxy", True):
            self.assertEqual(client_ip(request), "1.2.3.4")

    def test_forwarded_for_ignored_when_not_trusted(self):
        request = _make_request(forwarded_for="1.2.3.4")
        with patch.object(settings, "trust_proxy", False):
            self.assertEqual(client_ip(request), "9.9.9.9")


if __name__ == "__main__":
    unittest.main()
