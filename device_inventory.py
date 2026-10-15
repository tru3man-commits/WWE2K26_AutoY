"""Classify Windows PnP records without relying on translated device names."""
import re

NODE = re.compile(r'^(HID|USB|BTHENUM|BTHLEDEVICE|BTHLE)\\', re.I)
MICROSOFT = re.compile(r'VID_045E|VID&0*[12]?045E', re.I)
GAME_SERVICE = re.compile(r'^(xinputhid|xusb21|xusb22|xboxgip|xboxgipservice)$', re.I)
GAME_USAGE = re.compile(r'HID_DEVICE_SYSTEM_GAME|HID_DEVICE_UP:0001_U:000[45]', re.I)
XBOX_NAME = re.compile(r'xbox.*(controller|gamepad)', re.I)
VIRTUAL = re.compile(r'vigem|vjoy|virtual|ROOT\\RDP', re.I)
SHARED = re.compile(r'^(bthusb|usbhub|usbhub3|usbccgp)$', re.I)


def strings(value):
    if value is None:
        return []
    return [value] if isinstance(value, str) else [v for v in value if isinstance(v, str)]


def candidates_from_inventory(records):
    groups = {}
    for dev in records:
        device_id = dev.get('id') or ''
        if not NODE.search(device_id):
            continue
        ancestors = dev.get('ancestors') or []
        chain = [dev, *ancestors]
        if any(VIRTUAL.search(' '.join(str(x.get(k) or '') for k in ('id','service','name'))) for x in chain):
            continue
        service = dev.get('service') or ''
        name = dev.get('name') or ''
        if SHARED.match(service) or re.search(r'wireless adapter|bluetooth adapter|radio|hub', name, re.I):
            continue
        identity = ' '.join([device_id, *strings(dev.get('hardware'))])
        compatible = ' '.join(strings(dev.get('compatible')))
        # Bluetooth endpoints can have generic instance IDs; their vendor is
        # carried in HardwareID, while the controller role is in name/usage.
        game_service = bool(GAME_SERVICE.match(service))
        if not (MICROSOFT.search(identity) or game_service):
            continue
        if not (game_service or GAME_USAGE.search(compatible + ' ' + identity) or XBOX_NAME.search(name)):
            continue
        container = str(dev.get('container') or '').strip('{}').casefold()
        if container == '00000000-0000-0000-0000-000000000000':
            container = ''
        key = container or device_id.casefold()
        group = groups.setdefault(key, {'name':'Xbox controller', 'container':key, 'paths':[]})
        paths = [device_id]
        for parent in ancestors:
            parent_id = parent.get('id') or ''
            parent_container = str(parent.get('container') or '').strip('{}').casefold()
            if not container or parent_container != container or not NODE.search(parent_id):
                continue
            if SHARED.match(parent.get('service') or ''):
                continue
            if re.search(r'wireless adapter|bluetooth adapter|radio|hub', parent.get('name') or '', re.I):
                continue
            if MICROSOFT.search(parent_id) or parent_id.upper().startswith(('BTHENUM\\', 'BTHLE\\', 'BTHLEDEVICE\\')):
                paths.append(parent_id)
        for path in paths:
            if path.casefold() not in {p.casefold() for p in group['paths']}:
                group['paths'].append(path)
    result = list(groups.values())
    for group in result:
        transport = 'Bluetooth' if any('BTH' in p.upper() for p in group['paths']) else 'USB / wireless adapter'
        group['name'] = 'Xbox controller (' + transport + ')'
    return result
