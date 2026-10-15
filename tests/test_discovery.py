import unittest
from device_inventory import candidates_from_inventory as find


class DiscoveryTests(unittest.TestCase):
    def record(self, **changes):
        record = dict(id=r'HID\GENERIC_DEVICE\1', name='HID-compliant game controller',
                      service='HidBthLE', hardware=[r'HID\VID_045E&PID_0B13'],
                      compatible=['HID_DEVICE_UP:0001_U:0005'], container='controller-guid', ancestors=[])
        record.update(changes)
        return record

    def test_vendor_in_hardware_id_not_instance_id(self):
        self.assertEqual(len(find([self.record()])),1)

    def test_bluetooth_endpoint_named_xbox(self):
        dev=self.record(id=r'BTHLEDEVICE\GENERIC\1', name='Xbox Wireless Controller', compatible=[],
                        hardware=[r'BTHLEDevice\Dev_VID&02045E_PID&0B13'])
        result=find([dev]); self.assertEqual(len(result),1)
        self.assertIn('Bluetooth', result[0]['name'])

    def test_translated_name_with_xinput_service(self):
        dev=self.record(name='Unknown localized controller name',service='xinputhid',compatible=[],hardware=[])
        self.assertEqual(len(find([dev])),1)

    def test_microsoft_mouse_not_selected(self):
        dev=self.record(name='Microsoft mouse', compatible=['HID_DEVICE_SYSTEM_MOUSE'],service='mouhid')
        self.assertEqual(find([dev]),[])

    def test_vigem_ancestor_excludes_virtual_xbox(self):
        dev=self.record(ancestors=[dict(id=r'ROOT\SYSTEM\0001',service='ViGEmBus')])
        self.assertEqual(find([dev]),[])

    def test_shared_bluetooth_radio_never_hidden(self):
        dev=self.record(ancestors=[dict(id=r'USB\VID_045E&PID_9999\radio',service='BTHUSB',container='controller-guid')])
        self.assertEqual(find([dev])[0]['paths'],[dev['id']])

    def test_same_container_hid_and_bluetooth_grouped(self):
        one=self.record()
        two=self.record(id=r'BTHLEDEVICE\VID&02045E_PID&0B13\1',name='Xbox Wireless Controller',compatible=[])
        found=find([one,two]); self.assertEqual(len(found),1)
        self.assertEqual(len(found[0]['paths']),2)

    def test_wireless_adapter_not_selected(self):
        dev=self.record(name='Xbox Wireless Adapter for Windows',compatible=[])
        self.assertEqual(find([dev]),[])

    def test_null_hardware_arrays_are_supported(self):
        dev=self.record(service='xinputhid',hardware=[None],compatible=[None])
        self.assertEqual(len(find([dev])),1)

    def test_game_usage_in_hardware_ids_with_null_compatible(self):
        # Regression: Bluetooth Xbox exposes game usage in HardwareID while
        # CompatibleID is [null] and the service is blank.
        dev=self.record(service='', name='HID-compliant game controller',
                        hardware=[r'HID\VID_045E&PID_0B13', 'HID_DEVICE_SYSTEM_GAME',
                                  'HID_DEVICE_UP:0001_U:0005'], compatible=[None])
        self.assertEqual(len(find([dev])),1)

    def test_bluetooth_game_child_collects_only_its_parents(self):
        dev=self.record(service='', hardware=[r'HID\VID_045E&PID_0B13', 'HID_DEVICE_SYSTEM_GAME'],
                        compatible=[None], ancestors=[
                            dict(id=r'BTHLEDEVICE\VID&02045E_PID&0B13\hid', service='mshidumdf', container='controller-guid'),
                            dict(id=r'BTHLE\DEV_TEST\parent', service='BthLEEnum', container='controller-guid'),
                            dict(id=r'USB\VID_0489&PID_E0E2\radio', service='BTHUSB', container='system-guid')])
        candidates=find([dev])
        self.assertEqual(len(candidates),1)
        self.assertEqual(len(candidates[0]['paths']),3)
        self.assertFalse(any('VID_0489' in p for p in candidates[0]['paths']))
