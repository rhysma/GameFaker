# Fake Game Status for Discord

A tiny desktop app that lets you show **any text you want** as your "Playing" status on Discord. Type a fake game name in the box, click **Set Status**, and your friends see you "Playing" it.

- Works on **Windows** and **macOS** and **Linux**
- A single Python file with **no extra packages** to install
- Optional second line of text and a "time elapsed" timer
- Remembers your settings between runs

## Requirements

- **Python 3.8+**
  - Windows: install from [python.org](https://www.python.org/downloads/) and check **"Add python.exe to PATH"** during setup.
  - macOS: install from [python.org](https://www.python.org/downloads/). This version includes Tkinter, which the app uses for its window.
- The **Discord desktop app** running on the same computer. The browser version of Discord won't work.

## One-time setup: get a Discord Application ID

Discord only shows activity that comes from a registered app, so you need a free Application ID.

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and sign in.
2. Click **New Application** and give it any name (for example, `Game`).
3. On the **General Information** page, copy the **Application ID**.

You only need to do this once. The app saves the ID for next time.

## Usage

1. Download `fake_game_status.py`.
2. Run it:
   - **Windows:** double-click the file, or run:
     ```
     python fake_game_status.py
     ```
   - **macOS / Linux:** in Terminal, run:
     ```
     python3 fake_game_status.py
     ```
3. Paste your **Application ID** into the first box.
4. Type the game you want to "play".
5. Optionally, add a second line and choose whether to show the timer.
6. Press **Enter** or click **Set Status**.

Click **Clear** to remove the status. Closing the window also clears it.

## Tips & troubleshooting

| Problem | Fix |
|---|---|
| "Couldn't find Discord" | Make sure the Discord **desktop** app is open and you're logged in. |
| Status doesn't appear | In Discord, go to **User Settings → Activity Privacy** and turn on **"Share your detected activities"**. |
| "Discord refused the connection" | Double-check that you pasted the **Application ID**, not the Public Key or a token. |
| Member list shows the app's name instead of your text | Some Discord versions do this. Your full profile card still shows your text. To work around it, rename your application in the Developer Portal. |
| Status disappears | The app must stay open to keep the status. Minimizing it is fine. |

Settings are saved to `~/.fake_game_status.json` in your home folder.

## How it works

The app talks to the Discord desktop client through Discord's local RPC connection, the same one games use for Rich Presence. It uses a named pipe on Windows and a Unix socket on macOS and Linux. It sends a `SET_ACTIVITY` command with the text you typed. Nothing is sent over the internet except what Discord itself displays.

## Disclaimer

This is a just-for-fun project and is not affiliated with Discord.