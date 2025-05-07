import logging
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Union
import socket
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Error as PWError
from send2trash import send2trash
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)

CDP_ENDPOINT = "http://127.0.0.1:1337"   # 与 config 保持一致
REMOTE_PORT   = 1337

# ----------------------------------------------------------------------------
# Constant maps ----------------------------------------------------------------
# ----------------------------------------------------------------------------

DOMAIN_LIST = {
    "0": {
        "domain": "chrome",
        "software_name": "Google Chrome"
    },
    "1": {
        "domain": "clock",
        "software_name": "Clock"
    },
    "2": {
        "domain": "file_explorer",
        "software_name": "File Explorer"
    },
    "3": {
        "domain": "libreoffice_calc",
        "software_name": "Excel"
    },
    "4": {
        "domain": "libreoffice_writer",
        "software_name": "Word"
    },
    "5": {
        "domain": "microsoft_paint",
        "software_name": "Paint"
    },
    "6": {
        "domain": "msedge",
        "software_name": "Microsoft Edge"
    },
    "7": {
        "domain": "notepad",
        "software_name": "Notepad"
    },
    "8": {
        "domain": "settings",
        "software_name": "Settings"
    },
    "9": {
        "domain": "vlc",
        "software_name": "VLC media player"
    },
    "10": {
        "domain": "vs_code",
        "software_name": "VS Code"
    },
    "11": {
        "domain": "windows_calc",
        "software_name": "Calculator"
    }
}

EXE_MAP: Dict[str, str] = {
    "google-chrome": r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "msedge": r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "vlc": r"C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
}

# ----------------------------------------------------------------------------
# Helper functions ------------------------------------------------------------
# ----------------------------------------------------------------------------

def _shell_join(parts: List[str]) -> str:
    """Quote parts that contain spaces / special chars and join for PowerShell."""
    quoted = [f"'{p}'" if any(c in p for c in " &'\"") else p for p in parts]
    return " ".join(quoted)


def transform_launch(entry: Dict[str, Any]) -> Union[Dict[str, Any], None]:
    """Normalize launch commands for Windows platform."""
    cmd = entry["parameters"].get("command")
    cmd_list = cmd.split() if isinstance(cmd, str) else list(cmd)

    if cmd_list and cmd_list[0].lower() == "socat":  # drop socat for local run
        logger.info("Skipping socat launch entry - not needed on Windows.")
        return None

    if cmd_list and cmd_list[0].lower() == "start" and len(cmd_list) >= 2:
        prog, args = cmd_list[1].lower(), cmd_list[2:]
        if prog in EXE_MAP:
            cmd_list = [EXE_MAP[prog]] + args
    elif cmd_list and cmd_list[0] in EXE_MAP:
        cmd_list[0] = EXE_MAP[cmd_list[0]]

    entry["parameters"]["command"] = cmd_list
    return entry


def process_config(cfg: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for e in cfg:
        if e.get("type") == "launch":
            e = transform_launch(e)
            if e:
                out.append(e)
        else:
            out.append(e)
    return out

def _same_site(u1, u2):
    return urlparse(u1).netloc.lower() == urlparse(u2).netloc.lower()

def _port_open(host: str, port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.2)
    ok = s.connect_ex((host, port)) == 0
    s.close()
    return ok

# ----------------------------------------------------------------------------
# Controller ------------------------------------------------------------------
# ----------------------------------------------------------------------------

class WindowsSetupController:
    """Prepare benchmark tasks on a local Windows machine."""

    REMOTE_DEBUGGING_PORT = 1337

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        self._pw:          "sync_playwright | None" = None   # playwright client
        self._browser:     "Browser | None"          = None   # CDP Browser 对象
        self._chrome_context: "BrowserContext | None" = None  # 默认窗口的 context

    # ---------------------- top‑level dispatcher -----------------------------
    def setup(self, config_list: List[Dict[str, Any]]):
        for cfg in process_config(config_list):
            func = getattr(self, f"_{cfg['type']}_setup", None)
            if not func:
                logger.warning("Unsupported setup type: %s", cfg["type"])
                continue
            func(**cfg.get("parameters", {}))

    # ---------------------- generic helpers ---------------------------------
    def _launch_setup(self, command: Union[str, List[str]], shell: bool = False):
        # if _port_open("127.0.0.1", REMOTE_PORT):
        #     logger.info("Chrome CDP 端口已就绪，跳过再次启动")
        #     return
        # subprocess.run(["taskkill", "/IM", "chrome.exe", "/F"], shell=True,
        #            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        cmd_list = command.split() if isinstance(command, str) else list(command)
        cmd_name = cmd_list[0].lower()

        # cmd_list += [f"--user-data-dir={self.cache_dir}\\chrome-debug-profile"] # Chrome

        if cmd_name == "socat":
            logger.info("Skip launching socat command: %s", ' '.join(cmd_list))
            return

        if cmd_name == "start-process":
            ps_cmd = _shell_join(cmd_list)
        else:
            ps_cmd = "& " + _shell_join(cmd_list)

        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            shell=False
        )
        logger.info("Launched: %s", ps_cmd)

        # start = time.time()
        # while time.time() - start < 10:
        #     if _port_open("127.0.0.1", REMOTE_PORT):
        #         logger.info("Remote debugging port is open")
        #         return
        #     time.sleep(0.1)
        # raise RuntimeError(f"Timed out waiting for Chrome CDP port {REMOTE_PORT}")

    def _download_setup(self, files: List[Dict[str, str]]):
        for f in files:
            url, path = f["url"], f["path"]
            if os.path.exists(path):
                logger.info("Download skipped (exists): %s", path)
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(path, "wb") as fp:
                    for chunk in r.iter_content(8192):
                        fp.write(chunk)
            logger.info("Downloaded %s → %s", url, path)

    def _sleep_setup(self, seconds: float):
        logger.info("Sleeping %.1f s", seconds)
        time.sleep(seconds)

    def _open_setup(self, path: str):
        if not os.path.exists(path):
            logger.warning("Open failed - file not found: %s", path)
            return
        try:
            os.startfile(path)
            logger.info("Opened: %s", path)
        except Exception as e:
            logger.error("Failed to open %s: %s", path, e)

    def _activate_window_setup(self, window_name: str, **kwargs):
        import win32gui, win32con
        hwnd = win32gui.FindWindow(None, window_name)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            logger.info("Activated window: %s", window_name)
        else:
            logger.warning("Window not found: %s", window_name)

    def _execute_setup(self, command, stdout=None, stderr=None, shell=False, until=None):
        if isinstance(shell, str):
            shell = shell.lower() in {"true", "1", "yes"}
        cmd = command if shell or isinstance(command, list) else command.split()
        until = until or {}
        for attempt in range(5):
            res = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
            ok = (
                ("returncode" not in until or res.returncode == until["returncode"]) and
                ("stdout" not in until or until["stdout"] in res.stdout) and
                ("stderr" not in until or until["stderr"] in res.stderr)
            )
            if ok:
                Path(self.cache_dir).mkdir(exist_ok=True)
                if stdout:
                    Path(self.cache_dir, stdout).write_text(res.stdout, "utf-8")
                if stderr:
                    Path(self.cache_dir, stderr).write_text(res.stderr, "utf-8")
                logger.info("Execute succeeded: %s", cmd)
                return
            time.sleep(0.3)
        logger.warning("Execute did not meet conditions: %s", cmd)

    _command_setup = _execute_setup  # alias

    def _create_folder_setup(self, path: str):
        p = Path(os.path.expanduser(os.path.expandvars(path)))
        try:
            p.mkdir(parents=True, exist_ok=True)
            logger.info("Folder ready: %s", p)
        except Exception as e:
            logger.error("Failed to create folder %s: %s", p, e)

    def _recycle_file_setup(self, path: str):
        target = Path(os.path.expanduser(os.path.expandvars(path)))
        if not target.exists():
            logger.warning("Recycle - file not found: %s", target)
            return
        try:
            send2trash(str(target))
            logger.info("Sent to Recycle Bin: %s", target)
        except Exception as e:
            logger.error("Recycle failed for %s: %s", target, e)

    # ---------------------- Chrome tabs -------------------------------------
    def _ensure_chrome_context(self):
        if self._chrome_context:
            return

        if not self._pw:
            self._pw = sync_playwright().start()

        # 第一次连接
        if not self._browser:
            self._browser = self._pw.chromium.connect_over_cdp(CDP_ENDPOINT)
            logger.info("Connected to Chrome over CDP (%s)", CDP_ENDPOINT)

        # 取默认（第一个）BrowserContext；它对应最初打开的窗口
        if self._browser.contexts:
            self._chrome_context = self._browser.contexts[0]
        else:                              # 理论上几乎不会走到
            self._chrome_context = self._browser.new_context()

    def _chrome_open_tabs_setup(self, urls_to_open: List[str]):
        self._ensure_chrome_context()
        for url in urls_to_open:
            try:
                page = self._chrome_context.new_page()
                page.goto(url, timeout=30_000)
                logger.info("Opened tab: %s", url)
            except PWTimeoutError:
                logger.warning("Timeout opening %s", url)
            except Exception as e:
                logger.error("Error opening %s: %s", url, e)

    def _chrome_close_tabs_setup(self, urls_to_close: List[str]):
        self._ensure_chrome_context()
        targets = [u.rstrip('/').lower() for u in urls_to_close]
        for page in list(self._chrome_context.pages):
            try:
                cur = page.url.rstrip('/').lower()
                if any(_same_site(cur, tgt) for tgt in targets):
                    page.close()
                    logger.info("Closed tab: %s", cur)
            except Exception as e:
                logger.error("Error closing tab %s: %s", page.url, e)


    # ---------------------- Browser history ---------------------------------
    @staticmethod
    def _insert_history(db_path: str, history: List[Dict[str, Any]]):
        epoch0 = datetime(1601, 1, 1)
        conn = sqlite3.connect(db_path, timeout=10)
        cur = conn.cursor()
        for item in history:
            vt = datetime.now() - timedelta(seconds=item["visit_time_from_now_in_seconds"])
            ts = int((vt - epoch0).total_seconds() * 1_000_000)
            cur.execute("INSERT INTO urls(url, title, visit_count, typed_count, last_visit_time, hidden) VALUES(?,?,?,?,?,0)",
                        (item["url"], item["title"], 1, 0, ts))
            uid = cur.lastrowid
            cur.execute("INSERT INTO visits(url, visit_time, from_visit, transition, segment_id, visit_duration) VALUES(?,?,?,?,0,0)",
                        (uid, ts, 0, 805306368))
        conn.commit()
        conn.close()

    def _swap_db(self, orig: Path, tmp: Path):
        backup = orig.with_suffix(".bak")
        shutil.copy2(orig, backup)
        try:
            if orig.drive.lower() == tmp.drive.lower():
                # 同一盘符，可用原子替换
                os.replace(tmp, orig)
            else:
                # 不同盘符：先复制到目标，再删除原 tmp
                shutil.copy2(tmp, orig)
                os.remove(tmp)
            logger.info("History DB replaced - backup: %s", backup)
        except Exception as e:
            logger.error("Failed to swap DB: %s", e)

    def _prepare_history(self, orig_path: str, history: List[Dict[str, Any]]):
        orig = Path(os.path.expandvars(orig_path))
        if not orig.exists():
            logger.error("History DB not found: %s", orig)
            return
        fd, tmp_path = tempfile.mkstemp(prefix="Hist_", suffix=".sqlite", dir=self.cache_dir)
        os.close(fd)
        shutil.copy2(orig, tmp_path)
        for attempt in range(5):
            try:
                self._insert_history(tmp_path, history)
                break
            except sqlite3.OperationalError as e:
                logger.warning("DB locked, retry %d/5: %s", attempt + 1, e)
                time.sleep(1)
        else:
            logger.error("Failed to write history - giving up")
            return
        self._swap_db(orig, Path(tmp_path))

    def _update_browse_history_setup(self, history: List[Dict[str, Any]]):
        os.system("taskkill /IM chrome.exe /F >nul 2>&1")
        self._prepare_history(r"%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\History", history)

    def _update_browse_history_edge_setup(self, history: List[Dict[str, Any]]):
        os.system("taskkill /IM msedge.exe /F >nul 2>&1")
        self._prepare_history(r"%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\History", history)

    # ---------------------- shutdown ----------------------------------------
    def shutdown(self):
        if self._chrome_context:
            self._chrome_context.close()
        if self._pw:
            self._pw.stop()
        logger.info("Playwright resources closed")
