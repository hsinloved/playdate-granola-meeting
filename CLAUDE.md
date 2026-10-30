# Granola Remote for Playdate: project context for Claude Code

The user-facing guide is in README.md. This file is for agents working on the code.

## What it does
Press A on a Panic Playdate → the Mac helper sends ⇧⌘N to Granola → a new note opens
and Granola starts transcribing automatically. Press B → the helper clicks Granola's
stop control. Press Up → ping. Personal tool on a home or office LAN; not for Catalog.

## Architecture
```
Playdate (Lua, playdate.network.http) --HTTP GET /start|/stop|/ping?token=--> 
  mac-helper/granola_helper.py (stdlib ThreadingHTTPServer, port 8787)
    --> osascript / System Events --> Granola.app
```

## Verified facts (tested on the owner's Mac, SDK 3.1.2)
- The Granola API is read-only and can't start a recording, so UI automation is the only route.
- Granola is an Electron app. Its menus have no "new note" item. ⌘N does nothing.
  **⇧⌘N = New note**, and a new note starts transcribing on its own.
- Granola exposes **no accessibility tree** to System Events (`--find-ui ""` returns nothing),
  so `button` actions don't work. The `click_at` action (offset from a window corner) does.
- There's no known stop shortcut. Stop is a `click_at`, measured with `--where stop`.
- Playdate: **network calls must happen inside `playdate.update()`**. This includes
  `playdate.network.setEnabled` and `http.new`/`get`. Button callbacks only set
  `pendingAction`, and `update()` sends the request. Don't call the network API at load time
  or straight from button handlers.
- The Lua APIs used (`net.http.new(host, port, useHttps, reason)`, `setConnectTimeout`,
  `setRequestCompleteCallback`, `setConnectionClosedCallback`, `get`, `getResponseStatus`,
  `getBytesAvailable`, `read`, `getError`, `net.setEnabled(true, cb)`) work in the
  Simulator on SDK 3.1.2.

## Files
- `playdate/source/main.lua`: UI + request queue. `config.lua`: host, port, token, timeout.
- `mac-helper/granola_helper.py`: routes and CLI (`--test`, `--where [label]`,
  `--list-menus`, `--find-ui`). Action types: keystroke, menu, button, click_at, url, activate.
- `mac-helper/config.json`: token and actions. The repo copy contains placeholders only.
- `start-helper.command`: launcher for macOS Login Items.

## Rules
- Keep the helper **standard-library Python only**.
- Always require the token. Never commit a real token or IP.
- Playdate screen is 400×240, 1-bit.

## Roadmap: next update (requested by owner)
1. **Cover photo / launcher art.** Add 1-bit card and icon images under
   `playdate/source/` (e.g. a `launcher/` folder) and point `imagePath` in pdxinfo at
   them. Check the required file names and pixel sizes in *Inside Playdate*
   ("Game metadata" / launcher assets) for the installed SDK.
2. **Pause / resume.** Find Granola's pause control (hover it for a shortcut; otherwise
   use `--where pause`). Add a `pause` action (toggle) to config.json and a `/pause`
   route to the helper (generalise the `start`/`stop` route check). Map it to a Playdate
   button (e.g. Down, or Left/Right) and show a "paused" state on screen.
3. **Live transcript on the Playdate.** Unsolved. The Granola public API only returns
   finished notes (it needs both an AI summary and a transcript), so it can't stream.
   Options to investigate:
   a) Granola's local app data on the Mac (look under `~/Library/Application Support/Granola/`
      for a cache that updates during a meeting). This is unofficial and may break.
   b) Have the helper capture and transcribe audio itself (e.g. local Whisper). This
      means duplicate transcription and a non-stdlib dependency, so ask the owner first.
   Delivery: a `/transcript?since=N` route that returns the last few lines as plain text,
   polled from `update()` every ~1–2s while recording. Use word-wrapped, scrolling 1-bit
   text, and let the crank scroll back.

## Ideas / open tasks
- Find a sturdier stop method (a shortcut, if Granola adds one).
- A `/status` endpoint plus an on-device indicator.
- Crank-to-stop, a success sound, a 1-bit Granola graphic.
- Let the user edit the IP on the device (`playdate.datastore`) so it doesn't need a rebuild.
- A hidden LaunchAgent alternative to the Terminal launcher (needs Accessibility permission for python3).
