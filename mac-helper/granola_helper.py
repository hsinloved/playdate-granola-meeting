#!/usr/bin/env python3
"""
Granola helper: a tiny local HTTP server the Playdate calls.

  GET /ping?token=...    -> 200 "pong"
  GET /start?token=...   -> runs the configured "start" action in Granola
  GET /stop?token=...    -> runs the configured "stop" action (if set)

Also:  python3 granola_helper.py --test start   (runs the action once, no server)
       python3 granola_helper.py --where stop   (hover a button; prints a click_at line)
       python3 granola_helper.py --list-menus   (prints Granola's menu items)
       python3 granola_helper.py --find-ui TEXT (searches accessible UI elements;
                                                 Granola currently exposes none)

Standard library only. macOS only (uses osascript).
"""
import json
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text())
APP = CONFIG.get("app_name", "Granola")


def osascript(script: str) -> str:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "osascript failed")
    return r.stdout.strip()


def as_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def activate():
    osascript(f'tell application {as_str(APP)} to activate')
    time.sleep(CONFIG.get("activate_delay_seconds", 0.8))


def run_action(name: str):
    action = CONFIG["actions"].get(name)
    if not action:
        raise LookupError(f'no "{name}" action configured in config.json')
    kind = action["type"]

    if kind == "url":
        subprocess.run(["open", action["url"]], check=True)
        return

    activate()
    if kind == "menu":
        # e.g. {"type": "menu", "menu": "File", "item": "New Note"}
        osascript(f'''
tell application "System Events" to tell process {as_str(APP)}
    set frontmost to true
    click menu item {as_str(action["item"])} of menu {as_str(action["menu"])} of menu bar 1
end tell''')
    elif kind == "keystroke":
        # e.g. {"type": "keystroke", "key": "n", "modifiers": ["command"]}
        mods = ", ".join(f"{m} down" for m in action.get("modifiers", []))
        using = f" using {{{mods}}}" if mods else ""
        osascript(f'''
tell application "System Events" to tell process {as_str(APP)}
    set frontmost to true
    keystroke {as_str(action["key"])}{using}
end tell''')
    elif kind == "button":
        # e.g. {"type": "button", "text": "Quick Note"} — clicks the first UI
        # element in Granola's front window whose name/description contains text
        result = osascript(UI_SCAN.replace("__QUERY__", as_str(action["text"])).replace("__CLICK__", "true"))
        if not result.startswith("clicked"):
            raise RuntimeError(f'no button matching "{action["text"]}" found')
    elif kind == "click_at":
        # e.g. {"type": "click_at", "from": "top-right", "x": -90, "y": 45}
        # clicks a point relative to a corner of Granola's front window
        corner = action.get("from", "top-left")
        osascript(f'''
tell application "System Events" to tell process {as_str(APP)}
    set frontmost to true
    set {{wx, wy}} to position of front window
    set {{ww, wh}} to size of front window
    set px to wx + {action["x"]}
    set py to wy + {action["y"]}
    if {as_str(corner)} contains "right" then set px to wx + ww + {action["x"]}
    if {as_str(corner)} contains "bottom" then set py to wy + wh + {action["y"]}
    click at {{px, py}}
end tell''')
    elif kind == "activate":
        pass  # just bring Granola forward
    else:
        raise ValueError(f"unknown action type: {kind}")


# Scans Granola's front window. With __CLICK__ = false it lists matches;
# with true it clicks the first match. Electron apps only expose their UI to
# accessibility after AXManualAccessibility is set, so we set it first.
UI_SCAN = '''
tell application "System Events" to tell process "''' + APP + '''"
    set frontmost to true
    try
        set value of attribute "AXManualAccessibility" to true
    end try
    delay 0.6
    set q to __QUERY__
    set out to ""
    repeat with e in (entire contents of front window)
        try
            set label to ""
            try
                set label to (name of e as text)
            end try
            try
                set label to label & " | " & (description of e as text)
            end try
            try
                set label to label & " | " & (value of attribute "AXTitle" of e as text)
            end try
            if label contains q then
                set {ex, ey} to position of e
                set {ew, eh} to size of e
                if __CLICK__ then
                    try
                        perform action "AXPress" of e
                    on error
                        click at {ex + ew div 2, ey + eh div 2}
                    end try
                    return "clicked " & label
                end if
                set out to out & (role of e) & "  [" & label & "]  at " & ex & "," & ey & linefeed
            end if
        end try
    end repeat
    return out
end tell'''


def find_ui(text: str):
    activate()
    out = osascript(UI_SCAN.replace("__QUERY__", as_str(text)).replace("__CLICK__", "false"))
    print(out or f'Nothing matching "{text}". Try another word, or "" to list everything.')


def where(label: str = "start"):
    """Countdown, then report the mouse position relative to Granola's window
    and print a ready-to-paste click_at config line for `label`."""
    activate()
    for i in range(5, 0, -1):
        print(f"Hover your mouse over the button for '{label}'... {i}", flush=True)
        time.sleep(1)
    # NSEvent.mouseLocation is bottom-left based on the primary screen; System
    # Events uses top-left of the primary screen, so flip y.
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e",
        "ObjC.import('AppKit');var p=$.NSEvent.mouseLocation;"
        "var h=$.NSScreen.screens.objectAtIndex(0).frame.size.height;"
        "Math.round(p.x)+','+Math.round(h-p.y)"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    mx, my = (int(v) for v in r.stdout.strip().split(","))
    win = osascript(f'''
tell application "System Events" to tell process {as_str(APP)}
    set {{wx, wy}} to position of front window
    set {{ww, wh}} to size of front window
    return (wx as text) & "," & (wy as text) & "," & (ww as text) & "," & (wh as text)
end tell''')
    wx, wy, ww, wh = (int(float(v)) for v in win.split(","))
    dx, dy = mx - (wx + ww), my - wy
    print(f"\nMouse at {mx},{my}; Granola window at {wx},{wy} size {ww}x{wh}")
    if not (wx <= mx <= wx + ww and wy <= my <= wy + wh):
        print("Warning: the mouse wasn't inside Granola's window. Try again.")
    print(f'\nPut this in config.json under "actions":\n')
    print(f'    "{label}": {{ "type": "click_at", "from": "top-right", "x": {dx}, "y": {dy} }},')


def list_menus():
    print(osascript(f'''
tell application {as_str(APP)} to activate
delay 0.8
set out to ""
tell application "System Events" to tell process {as_str(APP)}
    repeat with m in menu bar items of menu bar 1
        set out to out & "== " & (name of m) & linefeed
        try
            repeat with i in menu items of menu 1 of m
                try
                    set n to name of i
                    if n is not missing value then set out to out & "   " & n & linefeed
                end try
            end repeat
        end try
    end repeat
end tell
return out'''))


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code: int, text: str):
        data = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        token = parse_qs(url.query).get("token", [""])[0] or self.headers.get("X-Token", "")
        if token != CONFIG["token"]:
            return self._reply(401, "bad token")
        route = url.path.strip("/")
        try:
            if route == "ping":
                return self._reply(200, "pong")
            if route in ("start", "stop"):
                run_action(route)
                return self._reply(200, f"{route} ok")
            return self._reply(404, "unknown route")
        except LookupError as e:
            return self._reply(501, str(e))
        except Exception as e:  # surface AppleScript errors to the Playdate screen
            return self._reply(500, str(e)[:200])

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {self.client_address[0]} {fmt % args}\n")


def main():
    if "--list-menus" in sys.argv:
        return list_menus()
    if "--where" in sys.argv:
        i = sys.argv.index("--where")
        return where(sys.argv[i + 1] if len(sys.argv) > i + 1 else "start")
    if "--find-ui" in sys.argv:
        i = sys.argv.index("--find-ui")
        return find_ui(sys.argv[i + 1] if len(sys.argv) > i + 1 else "")
    if "--test" in sys.argv:
        run_action(sys.argv[sys.argv.index("--test") + 1])
        return print("done")
    host, port = CONFIG.get("bind", "0.0.0.0"), CONFIG.get("port", 8787)
    print(f"Granola helper listening on http://{host}:{port}  (Ctrl+C to quit)")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
