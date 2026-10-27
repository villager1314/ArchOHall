import asyncio
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import socket
import tempfile
import threading
import time
import unittest
import zipfile

REPO=Path(__file__).resolve().parents[1]
BIN=REPO/'rootfs/usr/local/bin'
loader=importlib.machinery.SourceFileLoader('archohall_upower',str(BIN/'archohall-upower'))
spec=importlib.util.spec_from_loader(loader.name,loader)
power=importlib.util.module_from_spec(spec)
loader.exec_module(power)


class BatteryTests(unittest.TestCase):
    def test_discharge_charging_and_full(self):
        self.assertEqual(power.battery_properties({'battery':43,'batteryStatus':3})['State'],2)
        self.assertEqual(power.battery_properties({'battery':43,'plugged':True,'batteryStatus':2})['State'],1)
        self.assertEqual(power.battery_properties({'battery':100,'plugged':True,'batteryStatus':5})['State'],4)
        self.assertEqual(power.battery_properties({'battery':80,'plugged':True,'batteryStatus':4})['State'],5)

    def test_missing_state_is_not_an_empty_real_battery(self):
        self.assertFalse(power.battery_properties({})['IsPresent'])
        self.assertFalse(power.battery_properties({'battery':None})['IsPresent'])

    def test_stale_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json'
            p.write_text(json.dumps({'schema':1,'timestamp':100,'battery':43}))
            self.assertEqual(power.read_state(p),{})
            p.write_text(json.dumps({'schema':1,'timestamp':time.time()*1000,'battery':43}))
            self.assertEqual(power.read_state(p)['battery'],43)


class RequestTests(unittest.TestCase):
    def test_only_allowlisted_actions_are_written(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'requests').mkdir()
            env=dict(os.environ,ARCHOHALL_HOST_BRIDGE=d)
            result=subprocess.run(['bash',str(BIN/'archohall-host'),'shell; rm -rf /'],env=env,capture_output=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(list((Path(d)/'requests').iterdir()),[])

    def test_request_acknowledgement_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            inbox=Path(d)/'requests';inbox.mkdir()
            received=[]
            def host():
                deadline=time.monotonic()+4
                while time.monotonic()<deadline:
                    pending=list(inbox.glob('*.request'))
                    if pending:
                        p=pending[0];received.append(p.read_text().strip());p.with_suffix('.reply').write_text('OK\n');p.unlink();return
                    time.sleep(.02)
            worker=threading.Thread(target=host);worker.start()
            result=subprocess.run(['bash',str(BIN/'archohall-host'),'wifi'],env=dict(os.environ,ARCHOHALL_HOST_BRIDGE=d),capture_output=True,text=True)
            worker.join()
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(received,['wifi'])
            self.assertEqual(list(inbox.iterdir()),[])


class BusTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_bus_enumeration_and_property_update(self):
        from dbus_fast.aio import MessageBus
        try:
            check=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            check.close()
        except PermissionError:
            if os.environ.get('ARCHOHALL_ALLOW_RESTRICTED_SOCKET_SKIP') == '1':
                self.skipTest('Local executor forbids AF_UNIX; CI must run this test without the skip flag')
            raise
        with tempfile.TemporaryDirectory(prefix='archohall-') as d:
            address='unix:path='+d+'/archohall-system-bus'
            state=Path(d)/'state.json'
            state.write_text(json.dumps({'schema':1,'timestamp':time.time()*1000,'battery':43,'plugged':False,'batteryStatus':3}))
            daemon=await asyncio.create_subprocess_exec('dbus-daemon','--session','--nofork','--nopidfile','--address='+address,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            service=None;bus=None
            try:
                for _ in range(50):
                    if Path(d,'archohall-system-bus').exists():break
                    await asyncio.sleep(.02)
                ready=Path(d)/'ready'
                service=await asyncio.create_subprocess_exec('python3',str(BIN/'archohall-upower'),env=dict(os.environ,DBUS_SYSTEM_BUS_ADDRESS=address,ARCHOHALL_HOST_STATE=str(state),ARCHOHALL_UPOWER_READY=str(ready)),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                for _ in range(100):
                    if ready.exists():break
                    if service.returncode is not None:self.fail((await service.stderr.read()).decode())
                    await asyncio.sleep(.02)
                self.assertTrue(ready.exists())
                bus=await MessageBus(bus_address=address).connect()
                intro=await bus.introspect('org.freedesktop.UPower',power.ROOT)
                proxy=bus.get_proxy_object('org.freedesktop.UPower',power.ROOT,intro)
                interface=proxy.get_interface('org.freedesktop.UPower')
                self.assertEqual(await interface.call_enumerate_devices(),[power.DEVICE])
                intro=await bus.introspect('org.freedesktop.UPower',power.DEVICE)
                device=bus.get_proxy_object('org.freedesktop.UPower',power.DEVICE,intro).get_interface('org.freedesktop.DBus.Properties')
                props=await device.call_get_all('org.freedesktop.UPower.Device')
                self.assertEqual(props['Percentage'].value,43.0)
                state.write_text(json.dumps({'schema':1,'timestamp':time.time()*1000,'battery':44,'plugged':True,'batteryStatus':2}))
                await asyncio.sleep(2.2)
                props=await device.call_get_all('org.freedesktop.UPower.Device')
                self.assertEqual(props['Percentage'].value,44.0)
                self.assertEqual(props['State'].value,1)
            finally:
                if bus:bus.disconnect()
                for child in (service,daemon):
                    if child and child.returncode is None:child.terminate();await child.wait()


class PackagingTests(unittest.TestCase):
    def test_installer_rejects_upgrades_of_existing_frameworks(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            (directory/'id').write_text('#!/bin/sh\necho 0\n')
            (directory/'pacman').write_text('''#!/bin/sh
case "$1" in
    -Sp) echo 'kcoreaddons 6.99.0-1';;
    -Q) echo 'kcoreaddons 6.18.0-1';;
    *) echo INSTALL_WAS_ATTEMPTED >&2; exit 99;;
esac
''')
            for f in directory.iterdir():f.chmod(0o755)
            result=subprocess.run(['bash',str(BIN/'archohall-install-extras')],env=dict(os.environ,PATH=d+':'+os.environ['PATH']),capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertIn('kcoreaddons',result.stderr)
            self.assertNotIn('INSTALL_WAS_ATTEMPTED',result.stderr)

    def test_support_archive_is_guest_scoped_and_has_no_probe(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'support.zip'
            subprocess.run(['python3',str(REPO/'android/build_desktop_support.py'),str(p)],check=True)
            with zipfile.ZipFile(p) as z:
                names=z.namelist()
                self.assertTrue(all(n.startswith('usr/local/') and '..' not in n for n in names))
                self.assertFalse(any('probe' in n for n in names))
                self.assertIn('usr/local/bin/archohall-keyboard',names)
                self.assertIn('usr/local/share/archohall/quicksettings/org.kde.plasma.quicksetting.battery/contents/ui/main.qml',names)
                self.assertNotIn('usr/local/share/archohall/quicksettings/org.kde.plasma.quicksetting.settingsapp/metadata.json',names)


if __name__=='__main__':unittest.main()
