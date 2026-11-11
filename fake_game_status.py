"""
Fake Game Status for Discord
----------------------------
Type anything in the box and your Discord friends will see you "Playing" it.
Works on Windows and macOS (and Linux). Needs only Python 3 - no extra packages.

Requires the Discord DESKTOP app to be running on the same computer.
"""

import json
import os
import socket
import struct
import sys
import time
import uuid
import tkinter as tk
from tkinter import ttk

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".fake_game_status.json")

OP_HANDSHAKE, OP_FRAME, OP_CLOSE = 0, 1, 2


# --------------------------------------------------------------------------
# Minimal Discord local RPC client (talks to the Discord app on this computer)
# --------------------------------------------------------------------------
class DiscordIPC:
    def __init__(self, client_id):
        self.client_id = client_id
        self.pipe = None   # Windows named pipe
        self.sock = None   # macOS / Linux unix socket

    @staticmethod
    def _candidate_paths():
        if sys.platform == "win32":
            return [rf"\\?\pipe\discord-ipc-{i}" for i in range(10)]
        base = (os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TMPDIR")
                or os.environ.get("TMP") or os.environ.get("TEMP") or "/tmp")
        dirs = [base,
                os.path.join(base, "app", "com.discordapp.Discord"),  # Linux flatpak
                os.path.join(base, "snap.discord")]                    # Linux snap
        return [os.path.join(d, f"discord-ipc-{i}") for d in dirs for i in range(10)]

    def connect(self):
        for path in self._candidate_paths():
            try:
                if sys.platform == "win32":
                    self.pipe = open(path, "r+b", buffering=0)
                else:
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.settimeout(5)
                    s.connect(path)
                    self.sock = s
                break
            except OSError:
                continue
        else:
            raise ConnectionError("Couldn't find Discord. Make sure the Discord desktop app is open.")

        self._send(OP_HANDSHAKE, {"v": 1, "client_id": self.client_id})
        op, data = self._recv()
        if op == OP_CLOSE or data.get("evt") != "READY":
            msg = data.get("message") or (data.get("data") or {}).get("message") or "unknown error"
            self.close()
            raise ConnectionError(f"Discord refused the connection: {msg}\n(Check your Application ID.)")

    @property
    def connected(self):
        return self.pipe is not None or self.sock is not None

    def _write(self, b):
        if self.pipe:
            self.pipe.write(b)
            self.pipe.flush()
        else:
            self.sock.sendall(b)

    def _read(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.pipe.read(n - len(buf)) if self.pipe else self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Lost connection to Discord.")
            buf += chunk
        return buf

    def _send(self, op, payload):
        body = json.dumps(payload).encode("utf-8")
        self._write(struct.pack("<II", op, len(body)) + body)

    def _recv(self):
        op, length = struct.unpack("<II", self._read(8))
        return op, json.loads(self._read(length).decode("utf-8"))

    def set_activity(self, activity):
        """activity=None clears the status."""
        self._send(OP_FRAME, {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": os.getpid(), "activity": activity},
            "nonce": str(uuid.uuid4()),
        })
        op, data = self._recv()
        if op == OP_CLOSE:
            self.close()
            raise ConnectionError("Discord closed the connection.")
        if data.get("evt") == "ERROR":
            raise RuntimeError((data.get("data") or {}).get("message", "Discord returned an error."))

    def close(self):
        for h in (self.pipe, self.sock):
            try:
                if h:
                    h.close()
            except OSError:
                pass
        self.pipe = self.sock = None


# --------------------------------------------------------------------------
# The window
# --------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.ipc = None
        self.started_at = None

        root.title("Fake Game Status")
        root.resizable(False, False)

        cfg = self._load_config()
        self.client_id = tk.StringVar(value=cfg.get("client_id", ""))
        self.game = tk.StringVar(value=cfg.get("game", ""))
        self.line2 = tk.StringVar(value=cfg.get("line2", ""))
        self.show_timer = tk.BooleanVar(value=cfg.get("show_timer", True))
        self.status = tk.StringVar(value="Not connected.")

        f = ttk.Frame(root, padding=16)
        f.grid()

        ttk.Label(f, text="Discord Application ID").grid(row=0, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.client_id, width=42).grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))

        ttk.Label(f, text="Game you're \"playing\"").grid(row=2, column=0, sticky="w")
        game_entry = ttk.Entry(f, textvariable=self.game, width=42, font=("", 12))
        game_entry.grid(row=3, column=0, columnspan=2, sticky="we", pady=(0, 10))
        game_entry.bind("<Return>", lambda e: self.apply())

        ttk.Label(f, text="Second line (optional)").grid(row=4, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.line2, width=42).grid(row=5, column=0, columnspan=2, sticky="we", pady=(0, 10))

        ttk.Checkbutton(f, text="Show \"time elapsed\" timer", variable=self.show_timer).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Button(f, text="Set Status", command=self.apply).grid(row=7, column=0, sticky="we", padx=(0, 4))
        ttk.Button(f, text="Clear", command=self.clear).grid(row=7, column=1, sticky="we", padx=(4, 0))

        ttk.Label(f, textvariable=self.status, foreground="#555", wraplength=320).grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 0))

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        game_entry.focus()

    # ---- config ----
    def _load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    def _save_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
                json.dump({"client_id": self.client_id.get().strip(), "game": self.game.get(),
                           "line2": self.line2.get(), "show_timer": self.show_timer.get()}, fh)
        except OSError:
            pass

    # ---- actions ----
    def _ensure_connected(self):
        cid = self.client_id.get().strip()
        if not cid.isdigit():
            raise ValueError("Paste your Discord Application ID first (it's a long number).")
        if self.ipc and self.ipc.connected and self.ipc.client_id == cid:
            return
        if self.ipc:
            self.ipc.close()
        self.ipc = DiscordIPC(cid)
        self.ipc.connect()

    def _build_activity(self, with_display_type=True):
        game = self.game.get().strip()
        act = {"type": 0, "details": game}  # type 0 = "Playing"
        if with_display_type:
            # Makes the member list / friends list show "Playing <your text>"
            # instead of the Discord application's name.
            act["status_display_type"] = 2
        line2 = self.line2.get().strip()
        if line2:
            act["state"] = line2[:128] if len(line2) >= 2 else line2 + " "
        if self.show_timer.get():
            if self.started_at is None:
                self.started_at = int(time.time())
            act["timestamps"] = {"start": self.started_at}
        return act

    def apply(self):
        game = self.game.get().strip()
        if len(game) < 2:
            self.status.set("Type at least 2 characters for the game name.")
            return
        if len(game) > 128:
            self.status.set("Game name must be 128 characters or less.")
            return
        if not self.show_timer.get():
            self.started_at = None
        try:
            for attempt in range(2):  # retry once if the connection dropped
                try:
                    self._ensure_connected()
                    try:
                        self.ipc.set_activity(self._build_activity(True))
                    except RuntimeError:
                        # Older Discord versions may not accept status_display_type
                        self.ipc.set_activity(self._build_activity(False))
                    break
                except (ConnectionError, OSError):
                    if self.ipc:
                        self.ipc.close()
                    if attempt == 1:
                        raise
            self._save_config()
            self.status.set(f"✅ Now showing: Playing {game}\nKeep this window open (minimizing is fine).")
        except Exception as e:  # show any problem in the window
            self.status.set(f"⚠️ {e}")

    def clear(self):
        self.started_at = None
        try:
            if self.ipc and self.ipc.connected:
                self.ipc.set_activity(None)
            self.status.set("Status cleared.")
        except Exception as e:
            self.status.set(f"⚠️ {e}")

    def on_close(self):
        self._save_config()
        if self.ipc:
            try:
                self.ipc.set_activity(None)
            except Exception:
                pass
            self.ipc.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
