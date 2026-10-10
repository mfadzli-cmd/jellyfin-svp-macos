#!/usr/bin/env python3
"""Read interpolation status from a playing mpv instance; never control playback."""
import json
import socket
import sys
import time

PROPERTIES = ('mpv-version', 'container-fps', 'estimated-vf-fps', 'vf',
              'hwdec-current', 'frame-drop-count', 'decoder-frame-drop-count', 'pause')


def main():
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(5)
        sock.connect('/tmp/mpvsocket')
        stream = sock.makefile('r')
        def read_property(name, request_id):
            sock.sendall((json.dumps({'command': ['get_property', name],
                                     'request_id': request_id}) + '\n').encode())
            while True:
                line = stream.readline()
                if not line: raise RuntimeError('Player disconnected.')
                response = json.loads(line)
                if response.get('request_id') == request_id:
                    return response.get('data')
        def snapshot(offset):
            data = {p: read_property(p, offset + i) for i, p in enumerate(PROPERTIES)}
            # Do not print filter script paths, URLs, tokens, filenames, or account data.
            data['svp_filter_enabled'] = any(
                f.get('name') == 'vapoursynth' and f.get('label') == 'svp' and f.get('enabled', True)
                for f in data.pop('vf') or [])
            return data
        first = snapshot(100)
        time.sleep(5)
        second = snapshot(200)
        print(json.dumps({'start': first, 'end': second}, indent=2))
        active = (second['svp_filter_enabled'] and not second['pause']
                  and (second['estimated-vf-fps'] or 0) > (second['container-fps'] or 0) > 0)
        print('SVP interpolation observed.' if active else 'Not confirmed. Play a low-frame-rate video and retry.')
        print('This checks the player owning /tmp/mpvsocket; close other mpv-based players first.')
        return 0 if active else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f'Cannot verify: {exc}', file=sys.stderr)
        sys.exit(1)
