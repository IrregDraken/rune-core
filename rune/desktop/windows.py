from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any

if os.name == "nt":  # pragma: no cover - exercised on Windows
    import tkinter as tk
    from tkinter import ttk


API_DEFAULT = "http://127.0.0.1:8765"

# 40x40 transparent render of brand/rune-glyph.svg, kept inline so the
# desktop shell has no image-file dependency.
RUNE_GLYPH_PNG = "iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAYAAACM/rhtAAAABmJLR0QA/wD/AP+gvaeTAAADIklEQVRYhe2XTYgbZRzGf89Mim4VBcuytYWK33gUP0DBj0oLsnYTFVkQL+rB9SD4cVCriUw3BddaD/UgigUP9SDWD2K61I9D1SJWtMfKIggqsnbXikgFm20yj4dEu5XEvLPZbC95LpN35v88729eMvP+BwYaaKD/lUILS65WwJuBeaARYKkB84IZ0PRRZj8cYe31EE0Dn5U1VgiZNxcKKLzJMARcFOoBrjLcAp4YYd2P4DXgc4FNoQHBgIZZ4DLhXcAX3R3KGUZAN4K3gP+9McPcsgMC9Vb4obIKe0NNRVenBTfRXH0AhM8J9UcZADOr6OrlwgeAtcAc+CCA0XDRlSvPKOAiuPXAXEx6G/hVAIFElJwxwHZwie78FpSeqnL+cb891Cmjb4Cd4U5TCqxezVnXrShgIBzGdYAYrV8xwBA4IbWOboHGKwIYvnIabv3MNUGjX7plZ3kPdoB7/1LhT4F1wGxMvDFR/rt2tcbXtvbWGFio8dc33fJ7XsGIaOJ0uDvawm31e2uE8qfO6JMXNP5Ht/yeVzAifSUlIiV9LVH++84TrdoBPr81NHhbSH7PgInu+gF4smOBrRKV7eAH/zklvHNSha+XFdA0H0ETXVzyvmva1aR4QwpHc2gBGmcb3Sr2PQTRhkU5e2aobQ2dN7gfLPqDPwXBm3wbnTB6ervGdmUxZegHqZEd0MAx0Bsn0dSUtvye0Z/pPzgPXAC+t6zCW/+9mPhAzhx/KcWPgCLQl3XiwvMa/TUr1GIt206SaGN9m/KPCt1P8ym9YRX1cq+5y94sTCq/B/QYgGGi5EpPkH1pt8oae1n4xeZIxZKrTyw1q28N6yT5p4DdzZF3PufqA0vJ6V/LL3mGEw+D3wFk/HrRlbuzxvT1m2SvxhsxtfuAj4FY6M1nXbk5S0ZfAQESjS/U8D3AYWAoQtWSK1eH+vsOCLBDheMxuh2YAc4DfZR4+ooQ74oAAiQaOxaT2wz8BAw3aOx/xu9e2M2XBdDNw+Ivs2xKNPozMAr8BlwSk5vq5skAqN2CzxucPLhUQICy8kdSNAr6CtjfS9ZAAw0E/A0fWhnDLAXXdwAAAABJRU5ErkJggg=="


class WindowsDesktopShell:
    """A lightweight always-on-top RUNE Island for Windows.

    State comes from the RUNE API, chat is sent through the API, and this
    surface never grants node permissions by itself.
    """

    WIDTH = 460
    COLLAPSED_HEIGHT = 58
    EXPANDED_HEIGHT = 430
    POLL_MS = 2500

    def __init__(self, api_url: str = API_DEFAULT) -> None:
        if os.name != "nt":
            raise RuntimeError("WindowsDesktopShell can only run on Windows.")
        self.api_url = api_url.rstrip("/")
        self.session_token = os.environ.get("RUNE_SESSION_TOKEN", "")
        self.root = tk.Tk()
        self.root.title("RUNE")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#080b0a")
        self.root.resizable(False, False)
        self.expanded = False
        self._drag_offset: tuple[int, int] | None = None
        self._build()
        self._set_height(self.COLLAPSED_HEIGHT)
        self.root.after(100, self._poll)

    def _build(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Rune.TButton", background="#101713", foreground="#a8b9ae",
            borderwidth=0, padding=(9, 5), font=("Segoe UI", 8)
        )
        style.map("Rune.TButton", background=[("active", "#17221b")])

        outer = tk.Frame(
            self.root, bg="#080b0a", highlightthickness=1,
            highlightbackground="#23352a"
        )
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg="#0b100d", height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        for sequence, handler in (
            ("<ButtonPress-1>", self._drag_start),
            ("<B1-Motion>", self._drag_move),
            ("<Double-Button-1>", lambda _e: self.toggle()),
        ):
            header.bind(sequence, handler)

        import base64
        self.glyph_image = tk.PhotoImage(data=base64.b64decode(RUNE_GLYPH_PNG))
        glyph = tk.Label(
            header, image=self.glyph_image, bg="#0b100d", width=40, height=40
        )
        glyph.pack(side="left", padx=(12, 3))
        glyph.bind("<Button-1>", lambda _e: self.toggle())

        copy = tk.Frame(header, bg="#0b100d")
        copy.pack(side="left", fill="y", pady=8)
        tk.Label(
            copy, text="RUNE", fg="#e8eee9", bg="#0b100d",
            font=("Segoe UI Semibold", 9)
        ).pack(anchor="w")
        self.status_label = tk.Label(
            copy, text="STARTING", fg="#68756d", bg="#0b100d",
            font=("Consolas", 7)
        )
        self.status_label.pack(anchor="w")

        self.signal = tk.Label(
            header, text="●", fg="#3d4841", bg="#0b100d",
            font=("Segoe UI", 8)
        )
        self.signal.pack(side="right", padx=(0, 12))

        body = tk.Frame(outer, bg="#080b0a")
        body.pack(fill="both", expand=True)

        self.context_label = tk.Label(
            body, text="RUNE is here.", anchor="w",
            fg="#dce8df", bg="#080b0a", font=("Segoe UI Semibold", 13)
        )
        self.context_label.pack(fill="x", padx=18, pady=(16, 2))

        self.detail_label = tk.Label(
            body, text="Connecting to the local runtime...", anchor="w",
            justify="left", fg="#7f8d84", bg="#080b0a",
            font=("Segoe UI", 8), wraplength=420
        )
        self.detail_label.pack(fill="x", padx=18, pady=(0, 12))

        workspace_row = tk.Frame(body, bg="#080b0a")
        workspace_row.pack(fill="x", padx=14, pady=(0, 8))
        self.workspace_buttons: dict[str, ttk.Button] = {}
        for workspace_id in ("home", "work"):
            button = ttk.Button(
                workspace_row, text=workspace_id.upper(), style="Rune.TButton",
                command=lambda wid=workspace_id: self._workspace(wid)
            )
            button.pack(side="left", padx=3)
            self.workspace_buttons[workspace_id] = button

        self.window_list = tk.Listbox(
            body, height=7, bg="#0d1310", fg="#9eaaa2",
            selectbackground="#173523", selectforeground="#e7f7eb",
            relief="flat", borderwidth=0, font=("Consolas", 8),
            highlightthickness=1, highlightcolor="#1d3025"
        )
        self.window_list.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        composer = tk.Frame(body, bg="#080b0a")
        composer.pack(fill="x", padx=14, pady=(0, 14))
        self.input = tk.Entry(
            composer, bg="#0d1310", fg="#dfeae2",
            insertbackground="#7dffb2", relief="flat", font=("Segoe UI", 9)
        )
        self.input.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 7))
        self.input.bind("<Return>", self._send_chat)
        ttk.Button(
            composer, text="SEND", style="Rune.TButton",
            command=self._send_chat
        ).pack(side="right")

        self.root.bind("<Escape>", lambda _e: self.collapse())
        self.root.bind("<Button-3>", lambda _e: self.collapse())

    def _set_height(self, height: int) -> None:
        screen_w = self.root.winfo_screenwidth()
        x = max(0, (screen_w - self.WIDTH) // 2)
        self.root.geometry(f"{self.WIDTH}x{height}+{x}+12")

    def toggle(self) -> None:
        self.collapse() if self.expanded else self.expand()

    def expand(self) -> None:
        self.expanded = True
        self._set_height(self.EXPANDED_HEIGHT)
        self.input.focus_set()

    def collapse(self) -> None:
        self.expanded = False
        self._set_height(self.COLLAPSED_HEIGHT)

    def _drag_start(self, event: Any) -> None:
        self._drag_offset = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )

    def _drag_move(self, event: Any) -> None:
        if self._drag_offset is None:
            return
        x = event.x_root - self._drag_offset[0]
        y = max(0, event.y_root - self._drag_offset[1])
        self.root.geometry(f"+{x}+{y}")

    def _poll(self) -> None:
        threading.Thread(target=self._refresh, daemon=True).start()
        self.root.after(self.POLL_MS, self._poll)

    def _request(
        self, path: str, method: str = "GET",
        payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = None
        headers = {}
        if self.session_token:
            headers["X-RUNE-Session"] = self.session_token
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.api_url}{path}", data=data, headers=headers, method=method
        )
        with urllib.request.urlopen(request, timeout=1.5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _refresh(self) -> None:
        try:
            state = self._request("/api/state")
            windows = self._request("/api/windows").get("windows", [])
            self.root.after(0, lambda: self._apply_state(state, windows))
        except (OSError, urllib.error.URLError, ValueError) as exc:
            self.root.after(0, lambda: self._offline(str(exc)))

    def _apply_state(
        self, state: dict[str, Any], windows: list[dict[str, Any]]
    ) -> None:
        shell = state.get("shell", {})
        node = state.get("node", {})
        mode = shell.get("mode", "ambient")
        message = shell.get("island_message") or "ready"
        self.status_label.config(
            text=f"{mode.upper()} · {node.get('hostname', 'local node')}"
        )
        self.context_label.config(text=str(message)[:120])
        self.detail_label.config(
            text=(
                f"{len(windows)} visible windows · "
                f"{node.get('platform', 'unknown')} · "
                f"{node.get('observation', {}).get('process_count', 0)} processes"
            )
        )
        self.signal.config(fg="#7dffb2")
        self.window_list.delete(0, "end")
        for window in windows[:12]:
            marker = "●" if window.get("foreground") else "○"
            title = window.get("title", "Untitled")
            self.window_list.insert(
                "end", f"{marker}  {title}   PID {window.get('pid', '?')}"
            )
        if not windows:
            self.window_list.insert("end", "No window telemetry available.")
        for workspace in shell.get("workspaces", []):
            button = self.workspace_buttons.get(workspace.get("id"))
            if button:
                label = workspace.get("name", "").upper()
                button.config(
                    text=("● " if workspace.get("active") else "") + label
                )

    def _offline(self, reason: str) -> None:
        self.status_label.config(text="OFFLINE · START RUNE API")
        self.signal.config(fg="#68736d")
        self.detail_label.config(text=f"Runtime unavailable: {reason}")

    def _workspace(self, workspace_id: str) -> None:
        try:
            self._request(
                "/api/workspace", "POST",
                {"workspace_id": workspace_id, "message": f"activate {workspace_id}"}
            )
            self._refresh()
        except (OSError, urllib.error.URLError, ValueError):
            self._offline("workspace request failed")

    def _send_chat(self, _event: Any = None) -> None:
        message = self.input.get().strip()
        if not message:
            return
        self.input.delete(0, "end")
        self.status_label.config(text="THINKING")
        threading.Thread(
            target=self._send_chat_background, args=(message,), daemon=True
        ).start()

    def _send_chat_background(self, message: str) -> None:
        try:
            result = self._request("/api/chat", "POST", {"message": message})
            response = str(result.get("response", ""))
            self.root.after(0, lambda: self._chat_done(response))
        except (OSError, urllib.error.URLError, ValueError) as exc:
            self.root.after(0, lambda: self._offline(str(exc)))

    def _chat_done(self, response: str) -> None:
        self.status_label.config(text="AMBIENT")
        self.context_label.config(text=response[:120] or "Done.")
        self.expand()

    def run(self) -> None:
        self.root.mainloop()


def _api_is_online(api_url: str) -> bool:
    try:
        request = urllib.request.Request(f"{api_url.rstrip('/')}/api/health")
        with urllib.request.urlopen(request, timeout=0.6) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def main() -> None:
    api_url = os.environ.get("RUNE_API_URL", API_DEFAULT)
    session_token = os.environ.get("RUNE_SESSION_TOKEN") or secrets.token_urlsafe(32)
    api_process: subprocess.Popen[bytes] | None = None

    if not _api_is_online(api_url):
        child_env = os.environ.copy()
        child_env["RUNE_SESSION_TOKEN"] = session_token
        api_process = subprocess.Popen(
            [sys.executable, "-m", "rune.api"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=child_env,
        )
        for _ in range(12):
            if _api_is_online(api_url):
                break
            time.sleep(0.25)

    try:
        os.environ["RUNE_SESSION_TOKEN"] = session_token
        WindowsDesktopShell(api_url).run()
    finally:
        if api_process is not None and api_process.poll() is None:
            api_process.terminate()


if __name__ == "__main__":
    main()
