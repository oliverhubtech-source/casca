"""Detecção de navegadores instalados e montagem do comando de modo app."""

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import devices

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_WEBVIEW_RUNNER = _PROJECT_ROOT / "run_webview.py"
_FLATPAK_APP_ID = "io.github.oliverhubtech_source.Casca"


def _in_flatpak() -> bool:
    return "FLATPAK_ID" in os.environ


def _host_which(binary: str) -> str | None:
    """Localiza um binário no HOST. Dentro de um Flatpak o sandbox não enxerga os
    binários do sistema diretamente — precisa pedir pro host via flatpak-spawn
    (exige a permissão --talk-name=org.freedesktop.Flatpak no manifest)."""
    if not _in_flatpak():
        return shutil.which(binary)
    try:
        result = subprocess.run(
            ["flatpak-spawn", "--host", "which", binary],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    path = result.stdout.strip()
    return path if result.returncode == 0 and path else None


def _webkit_available() -> bool:
    try:
        import gi

        gi.require_version("WebKit", "6.0")
        from gi.repository import WebKit  # noqa: F401
    except (ValueError, ImportError):
        return False
    return True

# app_mode: "chromium" (--app=URL), "epiphany" (--application-mode) ou "firefox" (sem modo app real)
NATIVE_CANDIDATES = [
    ("google-chrome-stable", "Google Chrome", "chromium"),
    ("google-chrome", "Google Chrome", "chromium"),
    ("chromium-browser", "Chromium", "chromium"),
    ("chromium", "Chromium", "chromium"),
    ("brave-browser", "Brave", "chromium"),
    ("microsoft-edge-stable", "Microsoft Edge", "chromium"),
    ("microsoft-edge", "Microsoft Edge", "chromium"),
    ("vivaldi-stable", "Vivaldi", "chromium"),
    ("vivaldi", "Vivaldi", "chromium"),
    ("opera", "Opera", "chromium"),
    ("helium", "Helium", "chromium"),
    ("epiphany", "GNOME Web", "epiphany"),
    ("firefox", "Firefox", "firefox"),
    ("firefox-esr", "Firefox ESR", "firefox"),
]

FLATPAK_CANDIDATES = [
    ("com.google.Chrome", "Google Chrome", "chromium"),
    ("org.chromium.Chromium", "Chromium", "chromium"),
    ("com.brave.Browser", "Brave", "chromium"),
    ("com.microsoft.Edge", "Microsoft Edge", "chromium"),
    ("com.vivaldi.Vivaldi", "Vivaldi", "chromium"),
    ("com.opera.Opera", "Opera", "chromium"),
    ("org.gnome.Epiphany", "GNOME Web", "epiphany"),
    ("org.mozilla.firefox", "Firefox", "firefox"),
]


@dataclass(frozen=True)
class Browser:
    key: str  # identificador estável salvo no app criado
    label: str  # nome mostrado na interface
    kind: str  # "native" ou "flatpak"
    target: str  # binário ou app-id do flatpak
    app_mode: str  # "chromium", "epiphany" ou "firefox"

    def build_exec(
        self,
        url: str,
        profile_dir: str,
        wm_class: str,
        mobile: bool = False,
        device_key: str | None = None,
        browser_profile: str | None = None,
        width: int | None = None,
        height: int | None = None,
        title: str = "",
        header_color: str | None = None,
        text_color: str | None = None,
    ) -> str:
        if self.app_mode == "webkit":
            # Esse comando vai pro Exec= de um .desktop que o HOST (GNOME Shell) executa
            # diretamente — se o próprio Casca estiver rodando como Flatpak, "python3
            # <caminho>" não existe fora do sandbox, então precisa reentrar via `flatpak run`.
            if _in_flatpak():
                runner = f"flatpak run --command=casca-webview {_FLATPAK_APP_ID}"
            else:
                runner = f"python3 {shlex.quote(str(_WEBVIEW_RUNNER))}"
            command = (
                f'{runner} '
                f'--url={shlex.quote(url)} --title={shlex.quote(title)} '
                f'--data-dir={shlex.quote(profile_dir)} --wm-class={wm_class}'
            )
            if header_color:
                command += f' --color={shlex.quote(header_color)} --text-color={shlex.quote(text_color or "#ffffff")}'
            if width and height:
                command += f' --width={width} --height={height}'
            if mobile:
                device = devices.find_device(device_key)
                command += f' --user-agent={shlex.quote(device.user_agent)}'
            return command

        if self.kind == "native":
            launcher = shlex.quote(self.target)
        else:
            launcher = f"flatpak run {shlex.quote(self.target)}"

        if self.app_mode == "chromium":
            command = f'{launcher} --app={shlex.quote(url)} --class={wm_class} --name={wm_class}'
            if browser_profile:
                command += f' --profile-directory={shlex.quote(browser_profile)}'
            else:
                command += f' --user-data-dir={shlex.quote(profile_dir)}'
            if mobile:
                device = devices.find_device(device_key)
                command += f' --user-agent={shlex.quote(device.user_agent)}'
            if width and height:
                command += f' --window-size={width},{height}'
            return command
        if self.app_mode == "epiphany":
            # WebKitGTK/Epiphany não expõe flag de user-agent, tamanho de janela ou perfil/conta via CLI.
            return f'{launcher} --application-mode --profile={shlex.quote(profile_dir)} {shlex.quote(url)}'
        # firefox: não existe modo app nativo, abre em janela nova comum
        command = f'{launcher} --new-window {shlex.quote(url)}'
        if width and height:
            command += f' --width {width} --height {height}'
        return command

    @property
    def supports_isolated_profile(self) -> bool:
        return self.app_mode in ("chromium", "epiphany", "webkit")

    @property
    def supports_mobile_mode(self) -> bool:
        return self.app_mode in ("chromium", "firefox", "webkit")

    @property
    def supports_account_profile(self) -> bool:
        return self.app_mode == "chromium"

    @property
    def supports_header_color(self) -> bool:
        return self.app_mode == "webkit"


def _installed_flatpaks() -> set[str]:
    command = ["flatpak", "list", "--app", "--columns=application"]
    if _in_flatpak():
        # "flatpak list" de dentro do próprio sandbox só veria o Casca; pergunta ao host.
        command = ["flatpak-spawn", "--host", *command]
    elif not shutil.which("flatpak"):
        return set()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=True)
    except (subprocess.SubprocessError, OSError):
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


_detected_cache: list[Browser] | None = None


def detect_browsers(force_refresh: bool = False) -> list[Browser]:
    """Retorna os navegadores disponíveis: a janela própria do Casca (se houver WebKitGTK)
    primeiro, como padrão, seguida dos navegadores instalados (nativos e Flatpak).

    O resultado é cacheado em memória — a varredura envolve `shutil.which` para ~14
    candidatos e um `flatpak list` via subprocess, então repetir isso a cada criação/edição
    de app tem custo real. Passe `force_refresh=True` só se o usuário instalar/remover algo
    durante a sessão."""
    global _detected_cache
    if _detected_cache is not None and not force_refresh:
        return _detected_cache

    found: list[Browser] = []
    seen: set[tuple[str, str]] = set()

    if _webkit_available():
        found.append(
            Browser(key="webkit:casca", label="Janela própria do Casca", kind="native", target="", app_mode="webkit")
        )

    for binary, label, app_mode in NATIVE_CANDIDATES:
        path = _host_which(binary)
        if not path or (label, "native") in seen:
            continue
        seen.add((label, "native"))
        found.append(Browser(key=f"native:{binary}", label=label, kind="native", target=path, app_mode=app_mode))

    flatpaks = _installed_flatpaks()
    for app_id, label, app_mode in FLATPAK_CANDIDATES:
        if app_id not in flatpaks or (label, "flatpak") in seen:
            continue
        seen.add((label, "flatpak"))
        display = f"{label} (Flatpak)" if (label, "native") in seen else label
        found.append(Browser(key=f"flatpak:{app_id}", label=display, kind="flatpak", target=app_id, app_mode=app_mode))

    _detected_cache = found
    return found


def find_by_key(key: str, available: list[Browser] | None = None) -> Browser | None:
    for browser in available if available is not None else detect_browsers():
        if browser.key == key:
            return browser
    return None
