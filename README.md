# 🟡 Granola Remote for Playdate

> Press **A** on a little yellow handheld. A meeting note appears on your Mac. 🥣✨

Granola Remote turns your [Playdate](https://play.date) into a big, satisfying
"start taking notes" button for [Granola](https://granola.ai). One press opens a
new note, and Granola starts listening and transcribing. When the meeting's done,
press **B** to stop.

It doesn't save you much time over clicking. But you get to start meetings by
pressing a button on a tiny yellow console, which is a lot more fun.

```
  ┌─────────────┐      Wi-Fi      ┌──────────────┐   ⇧⌘N    ┌──────────┐
  │  Playdate   │ ──────────────▶ │  Mac helper  │ ───────▶ │ Granola  │
  │  Ⓐ  Ⓑ  ⬆️  │   "please, a    │  (tiny       │  "new    │  🎙️ 📝   │
  └─────────────┘    new note?"   │   Python)    │   note!" └──────────┘
                                  └──────────────┘
```

---

## 🤔 Why is there a "helper"?

Granola does have an API, but it's for *reading* notes after the meeting.
Nothing in it can say "start recording now." So a little helper program runs on
your Mac, listens for your Playdate, and presses Granola's buttons for you.

You **don't** need a Granola API key. You just need Granola open on your Mac.

---

## 🧺 What you'll need

- A **Playdate** on the same Wi-Fi as your Mac
- A **Mac** with **Granola** installed
- **Python 3** (type `python3 --version` in Terminal. If macOS offers to install
  developer tools, say yes and go make a tea ☕)
- The free **[Playdate SDK](https://play.date/dev/)**, to build the app

---

## 🛠️ Setup, in seven small steps

### 1. Get the code 📦

```bash
git clone https://github.com/hsinloved/playdate-granola-meeting.git ~/playdate-granola
cd ~/playdate-granola
```

### 2. Make a secret handshake 🤝

Your Playdate and your Mac share a password (the "token"), so nobody else on your
Wi-Fi can start your notes. This makes a random one and puts your Mac's IP
address in the app:

```bash
cd ~/playdate-granola
TOKEN=$(python3 -c "import secrets;print(secrets.token_urlsafe(16))")
IP=$(ipconfig getifaddr en0)
python3 -c "import json,sys;p='mac-helper/config.json';c=json.load(open(p));c['token']=sys.argv[1];json.dump(c,open(p,'w'),indent=2)" "$TOKEN"
sed -i '' -e "s/host = \".*\"/host = \"$IP\"/" -e "s/token = \".*\"/token = \"$TOKEN\"/" playdate/source/config.lua
grep -h token playdate/source/config.lua mac-helper/config.json
```

The token should show up twice, the same both times. Matching twins. 👯

> 💡 **Tip:** give your Mac a fixed IP in your router's settings (look for "DHCP
> reservation"). Otherwise your IP may change one day, and your Playdate will be
> shouting at an empty room.

### 3. Give the helper permission to press keys 🔐

Open Granola, then:

```bash
cd ~/playdate-granola/mac-helper
python3 granola_helper.py --test start
```

macOS will ask whether Terminal may control your computer. Go to **System
Settings → Privacy & Security → Accessibility** and switch **Terminal** on. Run
the command again, and a fresh Granola note should open. 🎉

### 4. Teach it where the stop button is 🛑

Granola has a shortcut for starting a note (⇧⌘N), but none for stopping. So the
helper clicks the stop button for you, and it needs to know where that is on
*your* screen.

Start a note so it's transcribing, then:

```bash
python3 granola_helper.py --where stop
```

You get a 5-second countdown. Rest your mouse on Granola's stop control (no
clicking!) and wait. It prints a line like this:

```
"stop": { "type": "click_at", "from": "top-right", "x": -734, "y": 132 },
```

Copy those numbers into the `"stop"` line in `mac-helper/config.json`. Then
check it works with `python3 granola_helper.py --test stop`.

> ⚠️ The stop click is measured from the window's top-right corner. If you resize
> Granola's window a lot, run `--where stop` again.

### 5. Build the Playdate app 🔨

```bash
cd ~/playdate-granola
~/Developer/PlaydateSDK/bin/pdc playdate/source GranolaRemote.pdx && echo "BUILD OK 🎉"
```

### 6. Try it in the Simulator 🧪

Start the helper in one Terminal window and **leave it running**:

```bash
cd ~/playdate-granola/mac-helper && python3 granola_helper.py
```

Open a **second** Terminal window (⌘N) and run:

```bash
cd ~/playdate-granola && open GranolaRemote.pdx
```

Click inside the Simulator, then:

| Button | What happens |
|---|---|
| **⬆️ Up** | Pings your Mac. You should see "Mac helper is reachable" 👋 |
| **Ⓐ A** | Opens a new Granola note. The circle fills in: you're recording! 🎙️ |
| **Ⓑ B** | Stops it 🛑 |

### 7. Send it to your Playdate 🚀

```bash
cd ~/playdate-granola && zip -r GranolaRemote.pdx.zip GranolaRemote.pdx && open .
```

Go to [play.date](https://play.date), then **Account → Sideload**, and drop in
`GranolaRemote.pdx.zip`. On your Playdate, open **Game Library**, refresh, and
download **Granola Remote**.

The first time you press **⬆️**, your Playdate asks whether the app may talk to
your Mac. Say yes. 💛

---

## 🌅 Make it start by itself when you log in

You don't need to open Terminal every morning:

1. Double-click **`start-helper.command`** once to check it works. (If macOS
   complains, right-click it and choose **Open**.)
2. Go to **System Settings → General → Login Items & Extensions**.
3. Under **Open at Login**, click **+** and pick `start-helper.command`.
4. While you're there, add **Granola** too, if it isn't already.

From now on, a Terminal window opens with the helper running each time you log
in. Minimize it if you like, but **don't close it**, or the helper stops.

---

## 🩹 When things go wobbly

| What you see | What's going on |
|---|---|
| **`Connection closed` / timeout** on the Playdate | The helper isn't running, the Playdate is on a different Wi-Fi, or your Mac's IP changed (go back to step 2 and rebuild). |
| **`Helper replied 401`** | The tokens don't match. Run step 2 again, rebuild, and restart the helper. |
| **`Helper replied 501`** | That action isn't set up in `config.json` yet (usually stop). |
| **`Helper replied 500`** | macOS blocked the keypress. Check Accessibility permissions (step 3). |
| Granola pops up but **no note appears** | Check the `start` line is ⇧⌘N, and that Granola is on its home screen. |
| **B clicks something random** | Granola's window changed size. Run `--where stop` again. |
| Typing in Terminal does **nothing** | You're typing into the window that's running the helper. Open a new one with ⌘N. |
| Simulator says **"Network access must be requested from playdate.update()"** | You're on an old `main.lua`. Pull the latest code. |

Each button press also adds a log line in the helper's window, like
`GET /start … 200`. **200** means it worked.

---

## 🗂️ What's in the box

```
playdate/source/
  main.lua          the Playdate app (buttons, screen, Wi-Fi bits)
  config.lua        your Mac's IP and the token
  pdxinfo           the app's name tag
mac-helper/
  granola_helper.py tiny web server that pokes Granola
  config.json       token, plus what "start" and "stop" do
start-helper.command  double-click launcher, also for Login Items
CLAUDE.md           notes for Claude Code if you want to keep building
```

### Helper commands

```bash
python3 granola_helper.py                # start listening
python3 granola_helper.py --test start   # try an action without the Playdate
python3 granola_helper.py --test stop
python3 granola_helper.py --where stop   # hover over a button, get a click_at line
python3 granola_helper.py --list-menus   # peek at Granola's menus
```

---

## 🔒 A little note on safety

- The helper only listens on your local network and ignores any request without
  the token.
- **Never** open port 8787 to the internet. If you want this away from home, use
  something like Tailscale.
- Your token and IP live in `config.json` and `config.lua`. If you fork this
  repo, don't commit your real ones.

---

## 🗺️ Roadmap

### Coming next ✨

- [ ] **🖼️ A proper cover photo.** A 1-bit card image and launcher icon, so Granola
      Remote looks great in the Playdate Game Library.
- [ ] **⏸️ Pause and resume.** Pause transcription for the off-the-record bits, then
      pick up where you left off. This needs a new button and a new `pause` action
      in the helper.
- [ ] **📜 Live transcript on the Playdate.** Watch the words scroll by on the tiny
      screen while Granola listens. This is the tricky one: Granola's API only shares
      notes *after* the meeting, so we'll need another way to peek at the live text.

### Someday, maybe 💭

- A cute 1-bit Granola bowl on the screen 🥣
- Crank to stop, because cranks are the best part of a Playdate
- A little *ding* when recording starts
- Show the latest meeting summary after the call

---

Made with 💛, one press of the A button at a time.

*Not affiliated with Panic or Granola. Just a fan with a yellow gadget and too many meetings.*
