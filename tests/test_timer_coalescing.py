"""Exercise the actual timer callback without importing Home Assistant."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/adaptive_alarm/controller.py"

class TimerTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_outstanding_tick_and_resume_after_completion(self):
        tree = ast.parse(SOURCE.read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "AdaptiveAlarmController")
        node = next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                    and n.name == "_on_timer")
        ns = {"callback": lambda fn: fn, "Any": object}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<timer>", "exec"), ns)
        callback = ns["_on_timer"]
        gate = asyncio.Event()
        tasks = []
        async def tick():
            await gate.wait()
        def create(coro):
            task = asyncio.create_task(coro)
            tasks.append(task)
            return task
        controller = SimpleNamespace(_tick_task=None, async_tick=tick,
                                     hass=SimpleNamespace(async_create_task=create))
        for _ in range(20):
            callback(controller, None)
        self.assertEqual(len(tasks), 1)
        gate.set()
        await tasks[0]
        callback(controller, None)
        await tasks[-1]
        self.assertEqual(len(tasks), 2)
