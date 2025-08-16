#!/usr/bin/env python3
# 👻 GhostCLI — Hacker Vibes OpenRouter Terminal Client (v0.2.0)
# Features: persona prompt, save API key to .env, SQLite session history
# https://github.com/amirrecon/GhostCLI

from __future__ import annotations

import json
import os
import random
import shutil
import sqlite3
import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

# ====== Paths ======
PKG_DIR = Path(__file__).resolve().parent
DATA_DIR = PKG_DIR  # ساده: کنار ماژول نگه می‌داریم
CONFIG_PATH = PKG_DIR / "ghostcli_config.json"
DB_PATH = PKG_DIR / "ghostcli.db"
ENV_PATH = Path.cwd() / ".env"

# ====== Defaults ======
DEFAULT_CONFIG: Dict[str, Any] = {
    "base_url": "https://openrouter.ai/api/v1",
    "model": "openai/gpt-4o-mini",
    "max_tokens": 1200,
    "temperature": 0.7,

    # امنیت
    "store_api_key": False,
    "api_key": "",

    # شخصی‌سازی
    "system_prompt": "You are GhostCLI, a helpful and safe hacker-style AI assistant.",
    "persona_prompt": "",   # پرومپت دید/شخصیتِ اضافه، همیشگی
    "user_prefix": "",

    # برندینگ/واترمارک
    "brand_text": "👻 GhostCLI — Powered by AmirRecon",
    "brand_mode": "random",  # off | left | right | random | floating

    # OpenRouter optional headers
    "site_name": "GhostCLI",
    "site_url": "https://github.com/amirrecon/GhostCLI",
}

ANSI_DIM = "\033[2m"
ANSI_RESET = "\033[0m"

BANNER = r"""
   ____ _               _    ____ _     ___ 
  / ___| |__   ___  ___| | _|  _ \ |   |_ _|
 | |  _| '_ \ / _ \/ __| |/ / | | | |    | | 
 | |_| | | | |  __/ (__|   <| |_| | |___ | | 
  \____|_| |_|\___|\___|_|\_\____/|_____|___|
        👻 GhostCLI — Hacker Vibes Terminal
"""

HELP_TEXT = """\
Commands:
/help                 → راهنما
/clear                → پاک کردن تاریخچه سشن فعلی
/model <name>         → تغییر مدل (مثلاً openai/gpt-4o-mini)
/sys <prompt>         → ست‌کردن system prompt و ریست تاریخچه
/persona <prompt>     → ست‌کردن persona prompt (ذهنیت/دید دائمی)
/pre <text>           → ست‌کردن prefix برای هر پیام کاربر (خالی = حذف)
/base <url>           → تغییر base URL (https://openrouter.ai/api/v1)
/brand <mode>         → off|left|right|random|floating
/brandtext <text>     → تغییر متن برندینگ
/temp <0..2>          → تغییر temperature
/max <int>            → تغییر max_tokens
/savekey <KEY>        → ذخیره کلید در config (امنیت کمتر)
/savekeyenv           → گرفتن API Key و ذخیره در .env (ترجیح امنیتی)
/whoami               → نمایش منبع کلید و تنظیمات فعلی

# Database (SQLite):
/session new          → ایجاد یک سشن جدید و سوییچ
/sessions             → لیست آخرین سشن‌ها (ID)
/use <id>             → سوییچ به یک سشن ذخیره‌شده
/history              → نمایش خلاصه‌ی پیام‌های سشن فعلی
/quit                 → خروج
"""

# ====== Utils ======

def load_config() -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                cfg.update(data)
        except Exception:
            pass
    return cfg

def save_config(cfg: Dict[str, Any]) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print("[✓] Config saved.")
    except Exception as e:
        print(f"[!] Failed to save config: {e}")

def term_width(default: int = 100) -> int:
    try:
        return shutil.get_terminal_size((default, 20)).columns
    except Exception:
        return default

def wrap(text: str, width: int = 100) -> str:
    return "\n".join(textwrap.wrap(text, width=width))

def branding_line(cfg: Dict[str, Any]) -> Optional[str]:
    mode = (cfg.get("brand_mode") or "off").lower()
    text = cfg.get("brand_text") or ""
    if not text or mode == "off":
        return None
    w = term_width()
    if mode == "left":
        line = text
    elif mode == "right":
        line = " " * max(0, w - len(text)) + text
    else:  # random / floating
        start = random.randint(0, max(0, w - len(text)))
        line = " " * start + text
    return f"{ANSI_DIM}{line}{ANSI_RESET}"

def print_branding(cfg: Dict[str, Any]) -> None:
    line = branding_line(cfg)
    if line:
        print(line)

def get_api_key(cfg: Dict[str, Any]) -> Optional[str]:
    # ENV اولویت دارد
    env_key = os.getenv("OPENROUTER_API_KEY")
    if env_key:
        return env_key.strip()
    if cfg.get("store_api_key") and cfg.get("api_key"):
        return str(cfg["api_key"]).strip()
    return None

def save_api_key_to_env_interactive() -> Optional[str]:
    print("\n[Security] OPENROUTER_API_KEY رو وارد کن (ذخیره میشه داخل .env در ریشه‌ی فعلی):")
    key = input("API Key: ").strip()
    if not key:
        print("[i] چیزی وارد نشد.")
        return None
    # .env موجود رو حفظ می‌کنیم/آپدیت می‌کنیم
    existing = ""
    if ENV_PATH.exists():
        existing = ENV_PATH.read_text(encoding="utf-8")
    lines = []
    found = False
    for line in existing.splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            lines.append(f"OPENROUTER_API_KEY={key}")
            found = True
        else:
            lines.append(line)
    if not found:
        lines.append(f"OPENROUTER_API_KEY={key}")
    ENV_PATH.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"[✓] ذخیره شد در {ENV_PATH}")
    return key

# ====== DB Layer (SQLite) ======

class GhostDB:
    def __init__(self, path: Path):
        self.path = path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init_db(self):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
            CREATE TABLE IF NOT EXISTS sessions(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              system_prompt TEXT,
              persona_prompt TEXT,
              user_prefix TEXT,
              model TEXT,
              base_url TEXT
            )""")
            c.execute("""
            CREATE TABLE IF NOT EXISTS messages(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id INTEGER,
              role TEXT,
              content TEXT,
              ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(session_id) REFERENCES sessions(id)
            )""")
            conn.commit()

    def create_session(self, *, system_prompt: str, persona_prompt: str,
                       user_prefix: str, model: str, base_url: str) -> int:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO sessions(system_prompt, persona_prompt, user_prefix, model, base_url)
                         VALUES(?,?,?,?,?)""", (system_prompt, persona_prompt, user_prefix, model, base_url))
            conn.commit()
            return c.lastrowid

    def add_message(self, session_id: int, role: str, content: str):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO messages(session_id, role, content) VALUES(?,?,?)""",
                      (session_id, role, content))
            conn.commit()

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""SELECT id, created_at, model, base_url FROM sessions
                        ORDER BY id DESC LIMIT ?""", (limit,))
            rows = c.fetchall()
        return [{"id": r[0], "created_at": r[1], "model": r[2], "base_url": r[3]} for r in rows]

    def load_messages(self, session_id: int) -> List[Dict[str, str]]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""SELECT role, content FROM messages WHERE session_id=?
                         ORDER BY id ASC""", (session_id,))
            rows = c.fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]

    def session_exists(self, session_id: int) -> bool:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM sessions WHERE id=?", (session_id,))
            return c.fetchone() is not None

# ====== OpenRouter Client ======

@dataclass
class ChatClient:
    base_url: str
    api_key: str
    model: str
    max_tokens: int = 1200
    temperature: float = 0.7
    site_name: Optional[str] = None
    site_url: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        h = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if self.site_url:
            h["HTTP-Referer"] = self.site_url
        if self.site_name:
            h["X-Title"] = self.site_name
        return h

    def chat(self, messages: List[Dict[str, str]], *, timeout: int = 60) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        backoff = 1.5
        for attempt in range(4):
            try:
                resp = requests.post(url, headers=self._headers(), json=payload, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(backoff); backoff *= 1.8; continue
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:400]}")
            except requests.RequestException as e:
                if attempt < 3:
                    time.sleep(backoff); backoff *= 1.8; continue
                raise RuntimeError(f"Network error: {e}") from e
        raise RuntimeError("Request failed after retries.")

# ====== App State / REPL ======

@dataclass
class GhostState:
    cfg: Dict[str, Any] = field(default_factory=load_config)
    messages: List[Dict[str, str]] = field(default_factory=list)
    db: GhostDB = field(default_factory=lambda: GhostDB(DB_PATH))
    session_id: Optional[int] = None

    def reset_history(self) -> None:
        """Initialize message history with system & persona prompts."""
        self.messages = []
        system = self.cfg.get("system_prompt") or DEFAULT_CONFIG["system_prompt"]
        persona = (self.cfg.get("persona_prompt") or "").strip()
        # دو پیام system می‌گذاریم: یکی برای قوانین، یکی برای دید/پرسونا (اگر ست شده)
        self.messages.append({"role": "system", "content": system})
        if persona:
            self.messages.append({"role": "system", "content": f"[Persona] {persona}"})

    def ensure_history(self) -> None:
        if not self.messages:
            self.reset_history()

    def start_new_session(self) -> None:
        self.reset_history()
        self.session_id = self.db.create_session(
            system_prompt=self.cfg.get("system_prompt") or DEFAULT_CONFIG["system_prompt"],
            persona_prompt=self.cfg.get("persona_prompt") or "",
            user_prefix=self.cfg.get("user_prefix") or "",
            model=self.cfg["model"],
            base_url=self.cfg["base_url"],
        )
        print(f"[✓] Session created: #{self.session_id}")

    def client(self) -> ChatClient:
        api_key = get_api_key(self.cfg)
        if not api_key:
            raise RuntimeError(
                "No API key found. Set OPENROUTER_API_KEY in .env or save with /savekey or /savekeyenv."
            )
        return ChatClient(
            base_url=self.cfg["base_url"],
            api_key=api_key,
            model=self.cfg["model"],
            max_tokens=int(self.cfg["max_tokens"]),
            temperature=float(self.cfg["temperature"]),
            site_name=self.cfg.get("site_name"),
            site_url=self.cfg.get("site_url"),
        )

# ====== Command Handling ======

def print_header(cfg: Dict[str, Any]) -> None:
    print(BANNER)
    print_branding(cfg)
    print("[💬] GhostCLI started. Empty input = /quit")
    print("[tip] /help برای لیست دستورات\n")

def handle_command(line: str, st: GhostState) -> bool:
    if not line.startswith("/"):
        return False
    parts = line.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) == 2 else ""

    if cmd in ("/quit", "/exit"):
        raise SystemExit

    if cmd == "/help":
        print(wrap(HELP_TEXT)); print_branding(st.cfg); return True

    if cmd == "/clear":
        st.reset_history()
        print("[✓] تاریخچه پاک شد."); print_branding(st.cfg); return True

    if cmd == "/model":
        if arg:
            st.cfg["model"] = arg.strip(); save_config(st.cfg)
            print(f"[✓] Model → {st.cfg['model']}")
        else:
            print(f"[i] Model: {st.cfg['model']}")
        print_branding(st.cfg); return True

    if cmd == "/sys":
        if arg:
            st.cfg["system_prompt"] = arg
            save_config(st.cfg)
            st.reset_history()
            print("[✓] System prompt updated & history reset.")
        else:
            print("[i] Current system prompt:\n" + st.cfg.get("system_prompt", ""))
        print_branding(st.cfg); return True

    if cmd == "/persona":
        st.cfg["persona_prompt"] = arg
        save_config(st.cfg)
        st.reset_history()
        print("[✓] Persona prompt set & history reset.")
        print_branding(st.cfg); return True

    if cmd == "/pre":
        st.cfg["user_prefix"] = arg
        save_config(st.cfg)
        print(f"[✓] Prefix set: {repr(arg)}"); print_branding(st.cfg); return True

    if cmd == "/base":
        if arg:
            st.cfg["base_url"] = arg.strip(); save_config(st.cfg)
            print(f"[✓] Base URL → {st.cfg['base_url']}")
        else:
            print(f"[i] Base URL: {st.cfg['base_url']}")
        print_branding(st.cfg); return True

    if cmd == "/brand":
        allowed = {"off", "left", "right", "random", "floating"}
        mode = arg.lower().strip()
        if mode in allowed:
            st.cfg["brand_mode"] = mode; save_config(st.cfg)
            print(f"[✓] Brand mode → {mode}")
        else:
            print("[i] Usage: /brand off|left|right|random|floating")
        print_branding(st.cfg); return True

    if cmd == "/brandtext":
        st.cfg["brand_text"] = arg; save_config(st.cfg)
        print("[✓] Brand text updated."); print_branding(st.cfg); return True

    if cmd == "/temp":
        try:
            t = float(arg); st.cfg["temperature"] = max(0.0, min(2.0, t))
            save_config(st.cfg); print(f"[✓] Temperature → {st.cfg['temperature']}")
        except Exception:
            print("[i] Usage: /temp <0..2>")
        print_branding(st.cfg); return True

    if cmd == "/max":
        try:
            mx = int(arg); st.cfg["max_tokens"] = max(1, mx)
            save_config(st.cfg); print(f"[✓] max_tokens → {st.cfg['max_tokens']}")
        except Exception:
            print("[i] Usage: /max <int>")
        print_branding(st.cfg); return True

    if cmd == "/savekey":
        if arg:
            st.cfg["api_key"] = arg.strip(); st.cfg["store_api_key"] = True
            save_config(st.cfg); print("[✓] API key saved in config (note: local storage risk).")
        else:
            print("[i] Usage: /savekey <KEY>")
        print_branding(st.cfg); return True

    if cmd == "/savekeyenv":
        key = save_api_key_to_env_interactive()
        if key:
            print("[✓] Now reload env (restart terminal) or I can try to load it now…")
            # Try to load immediately
            load_dotenv(ENV_PATH)
        print_branding(st.cfg); return True

    if cmd == "/whoami":
        src = "ENV" if os.getenv("OPENROUTER_API_KEY") else ("CONFIG" if st.cfg.get("store_api_key") else "NONE")
        print(f"Key source: {src}")
        print(f"Model: {st.cfg['model']}")
        print(f"Base URL: {st.cfg['base_url']}")
        persona = (st.cfg.get("persona_prompt") or "").strip()
        if persona:
            print("Persona: ✔ set")
        print_branding(st.cfg); return True

    # Database commands
    if cmd == "/session":
        if arg.strip().lower() == "new":
            st.start_new_session()
        else:
            print("[i] Usage: /session new")
        print_branding(st.cfg); return True

    if cmd == "/sessions":
        rows = st.db.list_sessions(limit=15)
        if not rows:
            print("[i] No sessions yet.")
        else:
            print("ID   | Created At           | Model")
            print("-----+----------------------+----------------------------")
            for r in rows:
                print(f"{r['id']:<4} | {r['created_at']:<20} | {r['model']}")
        print_branding(st.cfg); return True

    if cmd == "/use":
        try:
            sid = int(arg)
            if st.db.session_exists(sid):
                st.session_id = sid
                # بارگذاری تاریخچه برای نمایش فقط (state پیام‌ها رو از DB نمی‌ریزیم تو مموری، تمیزتره)
                st.reset_history()
                print(f"[✓] Switched to session #{sid}")
            else:
                print("[x] Session not found.")
        except Exception:
            print("[i] Usage: /use <id>")
        print_branding(st.cfg); return True

    if cmd == "/history":
        if st.session_id is None:
            print("[i] No session yet. Use /session new")
        else:
            msgs = st.db.load_messages(st.session_id)
            if not msgs:
                print("[i] Empty history.")
            else:
                for i, m in enumerate(msgs, 1):
                    head = "You " if m["role"] == "user" else "AI  "
                    print(f"{head}[{i}]: {m['content'][:120].replace('\\n',' ')}")
        print_branding(st.cfg); return True

    print("[i] Unknown command. /help"); print_branding(st.cfg); return True

def run_repl(st: GhostState) -> None:
    # load .env (if exists)
    load_dotenv(ENV_PATH)

    print_header(st.cfg)
    # start a session at first run
    st.start_new_session()

    while True:
        try:
            line = input("You: ").rstrip()
        except (EOFError, KeyboardInterrupt):
            print("\n[✓] Bye."); break

        if not line:
            line = "/quit"

        try:
            if handle_command(line, st):
                continue
        except SystemExit:
            print("[✓] Bye."); break

        # user message
        st.ensure_history()
        user_text = f"{st.cfg['user_prefix']}\n{line}" if st.cfg.get("user_prefix") else line
        st.messages.append({"role": "user", "content": user_text})

        # persist user message
        if st.session_id is not None:
            st.db.add_message(st.session_id, "user", user_text)

        # send
        try:
            client = st.client()
            content = client.chat(st.messages)
        except Exception as e:
            print(f"[x] {e}")
            print_branding(st.cfg)
            continue

        st.messages.append({"role": "assistant", "content": content})
        print("\nGhostCLI:\n")
        print(wrap(content))
        print()
        print_branding(st.cfg)

        # persist assistant message
        if st.session_id is not None:
            st.db.add_message(st.session_id, "assistant", content)

def main() -> None:
    # آرگومان‌های یک‌خطی ساده
    st = GhostState()
    for arg in sys.argv[1:]:
        if arg.startswith("--model="):
            st.cfg["model"] = arg.split("=", 1)[1]; save_config(st.cfg)
        elif arg.startswith("--base="):
            st.cfg["base_url"] = arg.split("=", 1)[1]; save_config(st.cfg)
        elif arg == "--nobrand":
            st.cfg["brand_mode"] = "off"; save_config(st.cfg)
        elif arg.startswith("--sys="):
            st.cfg["system_prompt"] = arg.split("=", 1)[1]; save_config(st.cfg)
        elif arg.startswith("--persona="):
            st.cfg["persona_prompt"] = arg.split("=", 1)[1]; save_config(st.cfg)
        elif arg.startswith("--pre="):
            st.cfg["user_prefix"] = arg.split("=", 1)[1]; save_config(st.cfg)

    run_repl(st)

if __name__ == "__main__":
    main()
