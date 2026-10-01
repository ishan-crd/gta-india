#!/usr/bin/env python3
"""Idempotent patches to the extracted Selkies AppImage so mouse look works over the stream.

1. input_handler.py: while the remote cursor is hidden (the game is in mouse-look), absolute client
   pointer positions are injected as deltas. Absolute XTEST warps otherwise reach the game's raw
   (relative) mouse input as whole screen coordinates and spin / pin the camera. Menus (cursor
   visible) keep absolute positioning.
2. selkies-core-*.js: a plain left click on the stream grabs browser pointer lock (true relative
   mouse, the cursor can't leave the window); stock Selkies needs Ctrl+Shift+click.

Usage: patch_selkies.py <squashfs-root>
"""
import glob
import os
import sys

ROOT = sys.argv[1]
TAG = "# GTA India patch"

HELPER = '''
    def _gi_cursor_hidden(self) -> bool:  # GTA India patch
        """True while the X cursor is blank (a game in mouse-look), cached for 100 ms."""
        now = time.monotonic()
        if now - getattr(self, "_gi_hidden_t", 0.0) > 0.1:
            self._gi_hidden_t = now
            hidden = False
            try:
                if self.xdisplay is not None and xfixes is not None:
                    if not getattr(self, "_xfixes_negotiated", False):
                        self.xdisplay.xfixes_query_version()
                        self._xfixes_negotiated = True
                    c = self.xdisplay.xfixes_get_cursor_image(self.xdisplay.screen().root)
                    hidden = not any((p >> 24) & 255 for p in c.cursor_image)
            except Exception:
                hidden = False
            self._gi_hidden = hidden
        return self._gi_hidden

    async def send_x11_mouse('''

CONVERT = '''        was_stale = self.tracked_position_stale
        # GTA India patch: absolute -> relative while the game hides the cursor.
        if relative:
            self._gi_abs_prev = None
        elif not self.wayland_input:
            prev = getattr(self, "_gi_abs_prev", None)
            self._gi_abs_prev = (x, y)
            if self._gi_cursor_hidden():
                dx, dy = (0, 0) if prev is None else (x - prev[0], y - prev[1])
                if abs(dx) > 400 or abs(dy) > 400:
                    dx, dy = 0, 0  # pointer left the stream and came back elsewhere: resync
                x, y, relative = dx, dy, True
                was_stale = self.tracked_position_stale
'''


def patch_py(path):
    s = open(path).read()
    if TAG in s:
        return "already"
    a = "\n    async def send_x11_mouse("
    b = "        was_stale = self.tracked_position_stale\n"
    assert s.count(a) == 1 and s.count(b) == 1, "selkies input_handler layout changed"
    s = s.replace(a, HELPER, 1).replace(b, CONVERT, 1)
    open(path, "w").write(s)
    return "patched"


def patch_js(path):
    s = open(path).read()
    old = "i&&e.button===0&&e.ctrlKey&&e.shiftKey&&this.shortcutsEnabled"
    new = "i&&e.button===0&&!this._isStreamLocked()"
    if new in s:
        return "already"
    assert old in s, "selkies core js layout changed"
    open(path, "w").write(s.replace(old, new, 1))
    return "patched"


for p in glob.glob(os.path.join(ROOT, "usr/conda/lib/python3.*/site-packages/selkies/input_handler.py")):
    print(p, patch_py(p))
for p in glob.glob(os.path.join(ROOT, "usr/conda/lib/python3.*/site-packages/selkies/selkies_web/assets/selkies-core-*.js")):
    print(p, patch_js(p))
