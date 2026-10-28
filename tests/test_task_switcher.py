import asyncio
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'rootfs/usr/local/bin/archohall-task-switcher'
loader = importlib.machinery.SourceFileLoader('task_switcher', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
switcher = importlib.util.module_from_spec(spec)
loader.exec_module(switcher)


class Process:
    returncode = None
    terminated = False

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    async def wait(self):
        return self.returncode


class TaskSwitcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_task_panel_dbus_contract_and_toggle(self):
        launched = []

        async def spawn(*args, **kwargs):
            launched.append((args, kwargs))
            return Process()

        service = switcher.TaskSwitcher(spawn)
        interface = service.introspect()
        method = next(m for m in interface.methods if m.name == 'invokeShortcut')
        self.assertEqual(method.in_signature, 's')
        self.assertEqual(method.out_signature, '')
        # The same call made by Plasma's TaskPanel::triggerTaskSwitcher.
        await switcher.TaskSwitcher.invokeShortcut.__wrapped__(service, 'unrelated shortcut')
        self.assertEqual(launched, [])
        await switcher.TaskSwitcher.invokeShortcut.__wrapped__(service, 'Mobile Task Switcher')
        self.assertEqual(len(launched), 1)
        self.assertEqual(launched[0][0], ('/usr/lib/qt6/bin/qml', '/usr/local/share/archohall/TaskSwitcher.qml'))
        process = service.process
        await switcher.TaskSwitcher.invokeShortcut.__wrapped__(service, 'Mobile Task Switcher')
        self.assertTrue(process.terminated)
        self.assertIsNone(service.process)
        await switcher.TaskSwitcher.invokeShortcut.__wrapped__(service, 'Mobile Task Switcher')
        self.assertEqual(len(launched), 2)

    async def test_simultaneous_presses_do_not_orphan_windows(self):
        processes = []

        async def spawn(*args, **kwargs):
            await asyncio.sleep(0)
            process = Process()
            processes.append(process)
            return process

        service = switcher.TaskSwitcher(spawn)
        await asyncio.gather(*(switcher.TaskSwitcher.invokeShortcut.__wrapped__(service, 'Mobile Task Switcher') for _ in range(4)))
        self.assertEqual(len(processes), 2)
        self.assertTrue(all(p.terminated for p in processes))
        self.assertIsNone(service.process)
