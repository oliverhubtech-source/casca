"""Interface do Casca: lista de web apps e formulário de criação/edição."""

import itertools
import threading
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

_header_class_counter = itertools.count()

from . import browsers, devices, entries, icons, presets, profiles, social_icons, store
from .fileutils import has_dangerous_scheme
from .headerbar_css import build_header_css


def _fold(text: str) -> str:
    """Normaliza texto para busca: minúsculo e sem acentos."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def _row_icon(path_str: str) -> Gtk.Widget:
    if path_str and Path(path_str).exists():
        image = Gtk.Image.new_from_file(path_str)
    else:
        image = Gtk.Image.new_from_icon_name("web-browser-symbolic")
    image.set_pixel_size(32)
    return image


def _color_bar(rgb: tuple[int, int, int]) -> Gtk.Widget:
    """Faixa vertical fina pintada com a cor dominante do ícone do app."""
    area = Gtk.DrawingArea()
    area.set_content_width(4)
    area.set_vexpand(True)
    area.set_valign(Gtk.Align.FILL)
    red, green, blue = (channel / 255 for channel in rgb)

    def draw(_area: Gtk.DrawingArea, cr, width: int, height: int) -> None:
        cr.set_source_rgb(red, green, blue)
        cr.rectangle(0, 0, width, height)
        cr.fill()

    area.set_draw_func(draw)
    return area


def _row_leading_widget(icon_path: str) -> Gtk.Widget:
    """Faixa colorida + ícone, para usar como prefixo de uma Adw.ActionRow."""
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    if icon_path and Path(icon_path).exists():
        box.append(_color_bar(icons.dominant_color(Path(icon_path))))
    box.append(_row_icon(icon_path))
    return box


def _build_icon_card(key: str, path, on_click) -> Gtk.Widget:
    button = Gtk.Button()
    button.add_css_class("flat")
    button.connect("clicked", lambda _btn: on_click(path))

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.CENTER)
    box.set_margin_top(6)
    box.set_margin_bottom(6)
    image = Gtk.Image.new_from_file(str(path))
    image.set_pixel_size(40)
    label = Gtk.Label(label=key.replace("-", " ").title(), wrap=True, justify=Gtk.Justification.CENTER)
    label.add_css_class("caption")
    box.append(image)
    box.append(label)
    button.set_child(box)
    return button


class IconGalleryDialog(Adw.Dialog):
    """Grade com os ícones de marcas incluídos no Casca, para usar em sites customizados."""

    def __init__(self, on_pick):
        super().__init__(title="Escolher ícone", content_width=480, content_height=600)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        scrolled = Gtk.ScrolledWindow(vexpand=True)
        flow = Gtk.FlowBox()
        flow.set_margin_top(12)
        flow.set_margin_bottom(12)
        flow.set_margin_start(18)
        flow.set_margin_end(18)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.set_row_spacing(6)
        flow.set_column_spacing(6)
        flow.set_min_children_per_line(4)
        flow.set_max_children_per_line(5)

        for key, path in social_icons.list_icons():
            flow.append(_build_icon_card(key, path, self._on_pick_and_close))

        scrolled.set_child(flow)
        toolbar.set_content(scrolled)
        self.set_child(toolbar)
        self._on_pick = on_pick

    def _on_pick_and_close(self, path) -> None:
        self._on_pick(path)
        self.close()


class IconSearchDialog(Adw.Dialog):
    """Busca ícones do site em várias fontes da internet e mostra os resultados numa grade."""

    def __init__(self, url: str, on_pick):
        super().__init__(title="Ícones encontrados", content_width=460, content_height=420)
        self._url = url
        self._on_pick = on_pick

        self._toolbar = Adw.ToolbarView()
        self._toolbar.add_top_bar(Adw.HeaderBar())
        self.set_child(self._toolbar)

        self._show_loading()
        threading.Thread(target=self._search_worker, daemon=True).start()

    def _show_loading(self) -> None:
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            valign=Gtk.Align.CENTER,
            vexpand=True,
        )
        spinner = Gtk.Spinner()
        spinner.set_size_request(32, 32)
        spinner.set_halign(Gtk.Align.CENTER)
        spinner.start()
        box.append(spinner)
        box.append(Gtk.Label(label="Buscando ícones na internet…"))
        self._toolbar.set_content(box)

    def _search_worker(self) -> None:
        results = icons.search_icons(self._url)
        GLib.idle_add(self._show_results, results)

    def _show_results(self, results: list[tuple[str, bytes]]) -> bool:
        if not results:
            status = Adw.StatusPage(
                icon_name="dialog-warning-symbolic",
                title="Nenhum ícone encontrado",
                description="Tente escolher uma imagem do computador ou da galeria.",
            )
            self._toolbar.set_content(status)
            return False

        scrolled = Gtk.ScrolledWindow(vexpand=True)
        flow = Gtk.FlowBox()
        flow.set_margin_top(12)
        flow.set_margin_bottom(12)
        flow.set_margin_start(18)
        flow.set_margin_end(18)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.set_row_spacing(8)
        flow.set_column_spacing(8)
        flow.set_min_children_per_line(3)
        flow.set_max_children_per_line(4)

        for index, (label, data) in enumerate(results):
            preview_path = icons.save_preview(data, f"result-{index}")
            flow.append(self._build_result_card(label, preview_path))

        scrolled.set_child(flow)
        self._toolbar.set_content(scrolled)
        return False

    def _build_result_card(self, label: str, path: Path) -> Gtk.Widget:
        button = Gtk.Button()
        button.add_css_class("flat")
        button.connect("clicked", lambda _btn: self._on_pick_and_close(path))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.CENTER)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        image = Gtk.Image.new_from_file(str(path))
        image.set_pixel_size(48)
        text = Gtk.Label(label=label, wrap=True, justify=Gtk.Justification.CENTER)
        text.add_css_class("caption")
        box.append(image)
        box.append(text)
        button.set_child(box)
        return button

    def _on_pick_and_close(self, path: Path) -> None:
        self._on_pick(path)
        self.close()


class EditorPage(Adw.NavigationPage):
    """Formulário de criação/edição de um web app."""

    def __init__(self, nav_view: Adw.NavigationView, on_saved, existing: entries.WebApp | None = None):
        super().__init__(title="Editar app" if existing else "Novo app")
        self._nav_view = nav_view
        self._on_saved = on_saved
        self._existing = existing
        self._detected_browsers = browsers.detect_browsers()
        self._picked_icon_path: Path | None = None
        self._auto_icon_path: Path | None = None

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self._header_css_class = f"casca-header-{next(_header_class_counter)}"
        header.add_css_class(self._header_css_class)
        self._header_css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), self._header_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        toolbar.add_top_bar(header)

        page = Adw.PreferencesPage()

        site_group = Adw.PreferencesGroup(title="Site")
        self._name_row = Adw.EntryRow(title="Nome do app")
        self._url_row = Adw.EntryRow(title="Endereço (URL)")
        site_group.add(self._name_row)
        site_group.add(self._url_row)
        page.add(site_group)

        browser_group = Adw.PreferencesGroup(title="Navegador")

        self._custom_browser_expander = Adw.ExpanderRow(
            title="Usar navegador personalizado",
            subtitle="Se desativado, abre na janela própria do Casca.",
        )
        self._custom_browser_expander.set_show_enable_switch(True)
        self._custom_browser_expander.set_enable_expansion(False)
        self._custom_browser_expander.connect("notify::enable-expansion", self._on_browser_changed)

        self._browser_row = Adw.ComboRow(title="Abrir com")
        labels = Gtk.StringList()
        for browser in self._detected_browsers:
            labels.append(browser.label)
        self._browser_row.set_model(labels)
        if not self._detected_browsers:
            self._browser_row.set_sensitive(False)
            self._custom_browser_expander.set_subtitle("Nenhum navegador compatível foi encontrado no sistema.")
        if browsers.in_flatpak():
            # Sandboxado, o Casca não detecta/oferece navegadores externos (ver
            # browsers.py) — a única opção real já é a janela própria, então o toggle
            # fica desabilitado em vez de mostrar uma lista com uma opção só.
            self._custom_browser_expander.set_sensitive(False)
            self._custom_browser_expander.set_subtitle(
                "Não disponível na versão Flatpak — use a instalação local para navegadores externos."
            )
        self._browser_row.connect("notify::selected", self._on_browser_changed)
        self._custom_browser_expander.add_row(self._browser_row)

        self._profile_row = Adw.ComboRow(title="Conta do navegador")
        self._profile_options: list[str | None] = [None]
        self._custom_browser_expander.add_row(self._profile_row)

        browser_group.add(self._custom_browser_expander)

        self._mobile_expander = Adw.ExpanderRow(
            title="Abrir em modo mobile",
            subtitle="Usa identificação e janela de um celular ou tablet.",
        )
        self._mobile_expander.set_show_enable_switch(True)
        self._mobile_expander.set_enable_expansion(False)
        self._mobile_expander.connect("notify::enable-expansion", self._on_mobile_toggled)

        self._device_row = Adw.ComboRow(title="Dispositivo")
        device_labels = Gtk.StringList()
        for device in devices.DEVICES:
            device_labels.append(device.label)
        self._device_row.set_model(device_labels)
        self._mobile_expander.add_row(self._device_row)

        browser_group.add(self._mobile_expander)
        page.add(browser_group)
        self._update_mobile_switch_availability()
        self._update_profile_options()

        resolution_group = Adw.PreferencesGroup()
        self._resolution_expander = Adw.ExpanderRow(
            title="Personalizar resolução da janela",
            subtitle="Se desativado, usa o tamanho padrão do navegador.",
        )
        self._resolution_expander.set_show_enable_switch(True)
        self._resolution_expander.set_enable_expansion(False)

        self._resolution_row = Adw.ComboRow(title="Tamanho da janela")
        resolution_modes = Gtk.StringList()
        for mode_label in ("Por dispositivo", "Tamanho padrão", "Personalizada"):
            resolution_modes.append(mode_label)
        self._resolution_row.set_model(resolution_modes)
        self._resolution_row.connect("notify::selected", self._on_resolution_mode_changed)
        self._resolution_expander.add_row(self._resolution_row)

        self._resolution_device_row = Adw.ComboRow(title="Dispositivo")
        self._resolution_device_row.set_model(device_labels)
        self._resolution_expander.add_row(self._resolution_device_row)

        self._resolution_preset_row = Adw.ComboRow(title="Tamanho")
        preset_sizes = Gtk.StringList()
        for size in devices.STANDARD_SIZES:
            preset_sizes.append(size.label)
        self._resolution_preset_row.set_model(preset_sizes)
        self._resolution_expander.add_row(self._resolution_preset_row)

        self._resolution_width_row = Adw.SpinRow(
            title="Largura", adjustment=Gtk.Adjustment(lower=200, upper=4000, step_increment=10, value=1024)
        )
        self._resolution_height_row = Adw.SpinRow(
            title="Altura", adjustment=Gtk.Adjustment(lower=200, upper=4000, step_increment=10, value=768)
        )
        self._resolution_expander.add_row(self._resolution_width_row)
        self._resolution_expander.add_row(self._resolution_height_row)

        resolution_group.add(self._resolution_expander)
        page.add(resolution_group)
        self._update_resolution_visibility()

        icon_group = Adw.PreferencesGroup()
        self._icon_expander = Adw.ExpanderRow(
            title="Personalizar ícone e atalho",
            subtitle="Se desativado, o ícone é buscado automaticamente e nenhum atalho é criado na Área de Trabalho.",
        )
        self._icon_expander.set_show_enable_switch(True)
        self._icon_expander.set_enable_expansion(False)

        icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, halign=Gtk.Align.CENTER)
        icon_box.set_margin_top(12)
        icon_box.set_margin_bottom(12)

        self._icon_preview = Gtk.Image.new_from_icon_name("image-missing-symbolic")
        self._icon_preview.set_pixel_size(56)
        icon_box.append(self._icon_preview)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.CENTER)
        search_button = Gtk.Button(label="Buscar na internet")
        search_button.connect("clicked", self._on_search_icons)
        choose_button = Gtk.Button(label="Do computador")
        choose_button.connect("clicked", self._on_choose_icon)
        gallery_button = Gtk.Button(label="Da galeria")
        gallery_button.connect("clicked", self._on_open_gallery)
        button_box.append(search_button)
        button_box.append(choose_button)
        button_box.append(gallery_button)
        icon_box.append(button_box)

        self._icon_expander.add_row(icon_box)

        self._desktop_switch_row = Adw.SwitchRow(title="Criar também na Área de Trabalho")
        self._icon_expander.add_row(self._desktop_switch_row)

        icon_group.add(self._icon_expander)
        page.add(icon_group)

        actions_group = Adw.PreferencesGroup()
        self._save_button = Gtk.Button(label="Criar app")
        self._save_button.add_css_class("suggested-action")
        self._save_button.add_css_class("pill")
        self._save_button.set_halign(Gtk.Align.CENTER)
        self._save_button.set_margin_top(12)
        self._save_button.connect("clicked", self._on_save)
        actions_group.add(self._save_button)
        page.add(actions_group)

        toolbar.set_content(page)
        self.set_child(toolbar)

        if existing:
            self._load_existing(existing)

    def _load_existing(self, app: entries.WebApp) -> None:
        self.set_title("Editar app")
        self._save_button.set_label("Salvar alterações")
        self._name_row.set_text(app.name)
        self._url_row.set_text(app.url)
        self._desktop_switch_row.set_active(app.desktop_shortcut)
        self._custom_browser_expander.set_enable_expansion(app.browser_key != "webkit:casca")
        for index, browser in enumerate(self._detected_browsers):
            if browser.key == app.browser_key:
                self._browser_row.set_selected(index)
                break
        self._update_mobile_switch_availability()
        self._mobile_expander.set_enable_expansion(app.mobile)
        for index, device in enumerate(devices.DEVICES):
            if device.key == app.device_key:
                self._device_row.set_selected(index)
                break
        self._update_profile_options()
        if app.browser_profile:
            try:
                self._profile_row.set_selected(self._profile_options.index(app.browser_profile))
            except ValueError:
                pass
        if app.width and app.height:
            self._resolution_expander.set_enable_expansion(True)
            self._resolution_row.set_selected(2)
            self._resolution_width_row.set_value(app.width)
            self._resolution_height_row.set_value(app.height)
        self._update_resolution_visibility()
        self._icon_expander.set_enable_expansion(True)
        if app.icon_path and Path(app.icon_path).exists():
            self._set_icon_preview(app.icon_path)

    def _set_icon_preview(self, path: str) -> None:
        self._icon_preview.set_from_file(path)
        self._apply_header_color(icons.dominant_color(Path(path)))

    def _apply_header_color(self, rgb: tuple[int, int, int]) -> None:
        color = icons.to_hex(rgb)
        text_color = icons.contrasting_text_color(rgb)
        css = build_header_css(self._header_css_class, color, text_color)
        self._header_css_provider.load_from_data(css.encode())

    def _on_browser_changed(self, *_args) -> None:
        self._update_mobile_switch_availability()
        self._update_profile_options()

    def _on_mobile_toggled(self, *_args) -> None:
        self._device_row.set_sensitive(self._mobile_expander.get_enable_expansion())

    def _on_resolution_mode_changed(self, *_args) -> None:
        self._update_resolution_visibility()

    def _update_resolution_visibility(self) -> None:
        mode = self._resolution_row.get_selected()
        self._resolution_device_row.set_visible(mode == 0)
        self._resolution_preset_row.set_visible(mode == 1)
        self._resolution_width_row.set_visible(mode == 2)
        self._resolution_height_row.set_visible(mode == 2)

    def _resolved_window_size(self) -> tuple[int | None, int | None]:
        if not self._resolution_expander.get_enable_expansion():
            return None, None
        mode = self._resolution_row.get_selected()
        if mode == 0:
            device = devices.DEVICES[self._resolution_device_row.get_selected()]
            return device.width, device.height
        if mode == 1:
            size = devices.STANDARD_SIZES[self._resolution_preset_row.get_selected()]
            return size.width, size.height
        if mode == 2:
            return int(self._resolution_width_row.get_value()), int(self._resolution_height_row.get_value())
        return None, None

    def _current_browser(self) -> browsers.Browser | None:
        if not self._custom_browser_expander.get_enable_expansion():
            return next((b for b in self._detected_browsers if b.key == "webkit:casca"), None)
        selected = self._browser_row.get_selected()
        if selected == Gtk.INVALID_LIST_POSITION or not self._detected_browsers:
            return None
        return self._detected_browsers[selected]

    def _update_mobile_switch_availability(self) -> None:
        browser = self._current_browser()
        supported = browser is not None and browser.supports_mobile_mode
        self._mobile_expander.set_sensitive(supported)
        if not supported:
            self._mobile_expander.set_enable_expansion(False)
            self._mobile_expander.set_subtitle(
                f"{browser.label} não suporta modo mobile." if browser else "Escolha um navegador."
            )
        else:
            self._mobile_expander.set_subtitle("Usa identificação e janela de um celular ou tablet.")

    def _update_profile_options(self) -> None:
        browser = self._current_browser()
        found = profiles.list_profiles(browser) if browser and browser.supports_account_profile else []

        labels = Gtk.StringList()
        labels.append("Perfil isolado (novo, sem login)")
        self._profile_options = [None]
        for profile in found:
            labels.append(profile.label)
            self._profile_options.append(profile.directory)

        self._profile_row.set_model(labels)
        self._profile_row.set_selected(0)
        self._profile_row.set_sensitive(browser is not None and browser.supports_account_profile)

    def _on_fetch_favicon(self, _button: Gtk.Button) -> None:
        url = self._url_row.get_text().strip()
        if not url:
            self._toast("Digite a URL antes de buscar o ícone.")
            return
        data = icons.fetch_favicon(url)
        if not data:
            self._toast("Não foi possível buscar o ícone automaticamente.")
            return
        temp_path = Path(GLib.get_tmp_dir()) / "casca-favicon-preview.png"
        temp_path.write_bytes(data)
        self._auto_icon_path = temp_path
        self._picked_icon_path = None
        self._set_icon_preview(str(temp_path))

    def _on_search_icons(self, _button: Gtk.Button) -> None:
        url = self._url_row.get_text().strip()
        if not url:
            self._toast("Digite a URL antes de buscar o ícone.")
            return
        dialog = IconSearchDialog(url, on_pick=self._on_search_icon_picked)
        dialog.present(self)

    def _on_search_icon_picked(self, path: Path) -> None:
        self._picked_icon_path = path
        self._auto_icon_path = None
        self._set_icon_preview(str(path))

    def _on_choose_icon(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog(title="Escolher imagem do ícone")
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Imagens")
        filter_images.add_mime_type("image/png")
        filter_images.add_mime_type("image/jpeg")
        filter_images.add_mime_type("image/svg+xml")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_images)
        dialog.set_filters(filters)
        dialog.open(self.get_ancestor(Gtk.Window), None, self._on_icon_chosen)

    def _on_icon_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error:
            return
        if gfile is None:
            return
        path = Path(gfile.get_path())
        self._picked_icon_path = path
        self._auto_icon_path = None
        self._set_icon_preview(str(path))

    def _on_preset_picked(self, preset: presets.Preset) -> None:
        self._name_row.set_text(preset.name)
        self._url_row.set_text(preset.url)
        bundled_icon = social_icons.get_icon_path(preset.icon_key)
        if bundled_icon:
            self._auto_icon_path = bundled_icon
            self._picked_icon_path = None
            self._set_icon_preview(str(bundled_icon))
        else:
            self._on_fetch_favicon(None)

    def _on_store_item_picked(self, item: "store.StoreItem") -> None:
        self._name_row.set_text(item.name)
        self._url_row.set_text(item.url)
        icon_path = store.save_icon_to_temp(item)
        if icon_path:
            self._auto_icon_path = icon_path
            self._picked_icon_path = None
            self._set_icon_preview(str(icon_path))
        else:
            self._on_fetch_favicon(None)

    def _on_open_gallery(self, _button: Gtk.Button) -> None:
        dialog = IconGalleryDialog(on_pick=self._on_gallery_icon_picked)
        dialog.present(self)

    def _on_gallery_icon_picked(self, path: Path) -> None:
        self._picked_icon_path = path
        self._auto_icon_path = None
        self._set_icon_preview(str(path))

    def _toast(self, message: str) -> None:
        toast = Adw.Toast(title=message, timeout=3)
        root = self.get_ancestor(Gtk.Window)
        if isinstance(root, CascaWindow):
            root.toast_overlay.add_toast(toast)

    def _on_save(self, _button: Gtk.Button) -> None:
        name = self._name_row.get_text().strip()
        url = self._url_row.get_text().strip()

        if not name or not url:
            self._toast("Preencha o nome e a URL do site.")
            return
        if has_dangerous_scheme(url):
            self._toast("Use um endereço http:// ou https://.")
            return
        if "://" not in url:
            url = f"https://{url}"
        if urlparse(url).scheme not in ("http", "https"):
            self._toast("Use um endereço http:// ou https://.")
            return

        if self._custom_browser_expander.get_enable_expansion():
            selected = self._browser_row.get_selected()
            if selected == Gtk.INVALID_LIST_POSITION or not self._detected_browsers:
                self._toast("Escolha um navegador.")
                return
            browser_key = self._detected_browsers[selected].key
            profile_selected = self._profile_row.get_selected()
            browser_profile = (
                self._profile_options[profile_selected] if profile_selected != Gtk.INVALID_LIST_POSITION else None
            )
        else:
            webkit_browser = next((b for b in self._detected_browsers if b.key == "webkit:casca"), None)
            if webkit_browser is None:
                self._toast("Janela própria do Casca não disponível. Marque 'Usar navegador personalizado'.")
                return
            browser_key = webkit_browser.key
            browser_profile = None

        mobile = self._mobile_expander.get_enable_expansion()
        device_key = devices.DEVICES[self._device_row.get_selected()].key if mobile else None
        width, height = self._resolved_window_size()

        if self._icon_expander.get_enable_expansion():
            desktop_shortcut = self._desktop_switch_row.get_active()
            icon_source = self._picked_icon_path or self._auto_icon_path
        else:
            # personalização desativada: ignora escolha manual, mantém o que já foi
            # resolvido automaticamente (ex.: ícone de um predefinido) e sem atalho.
            desktop_shortcut = False
            icon_source = self._auto_icon_path

        try:
            if self._existing:
                entries.update_app(
                    self._existing.slug,
                    name,
                    url,
                    browser_key,
                    icon_source,
                    desktop_shortcut,
                    mobile,
                    device_key,
                    browser_profile,
                    width,
                    height,
                )
            else:
                if icon_source is None:
                    data = icons.fetch_favicon(url)
                    slug_guess = entries.slugify(name)
                    icon_source = icons.save_icon_from_bytes(data, slug_guess) if data else None
                if icon_source is None:
                    self._toast("Não foi possível definir um ícone. Escolha uma imagem manualmente.")
                    return
                entries.create_app(
                    name,
                    url,
                    browser_key,
                    icon_source,
                    desktop_shortcut,
                    mobile,
                    device_key,
                    browser_profile,
                    width,
                    height,
                )
        except (ValueError, KeyError, OSError) as error:
            self._toast(f"Erro ao salvar: {error}")
            return

        self._on_saved()
        self._nav_view.pop()


class PresetsPage(Adw.NavigationPage):
    """Tela com a lista de sites pré-definidos, agrupados por categoria."""

    def __init__(self, nav_view: Adw.NavigationView, on_refresh_list):
        super().__init__(title="Site pré-definido")
        self._nav_view = nav_view
        self._on_refresh_list = on_refresh_list

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        self._search_entry = Gtk.SearchEntry(placeholder_text="Buscar por nome ou categoria…")
        self._search_entry.set_margin_start(12)
        self._search_entry.set_margin_end(12)
        self._search_entry.set_margin_top(12)
        self._search_entry.connect("changed", self._on_search_changed)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        group = Adw.PreferencesGroup()
        self.category_expanders: list[Adw.ExpanderRow] = []
        self._category_rows: list[tuple[presets.PresetCategory, Adw.ExpanderRow, list[tuple[presets.Preset, Adw.ActionRow]]]] = []
        for category in presets.PRESET_CATEGORIES:
            expander = Adw.ExpanderRow(title=category.title, subtitle=f"{len(category.presets)} sites")
            rows = []
            for preset in category.presets:
                row = self._build_preset_row(preset)
                expander.add_row(row)
                rows.append((preset, row))
            group.add(expander)
            self.category_expanders.append(expander)
            self._category_rows.append((category, expander, rows))
        page.add(group)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.append(self._search_entry)
        content_box.append(page)

        toolbar.set_content(content_box)
        self.set_child(toolbar)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        query = _fold(entry.get_text().strip())

        if not query:
            for _category, expander, rows in self._category_rows:
                expander.set_visible(True)
                expander.set_expanded(False)
                for _preset, row in rows:
                    row.set_visible(True)
            return

        for category, expander, rows in self._category_rows:
            category_matches = query in _fold(category.title)
            any_visible = False
            for preset, row in rows:
                visible = category_matches or query in _fold(preset.name)
                row.set_visible(visible)
                any_visible = any_visible or visible
            expander.set_visible(any_visible)
            expander.set_expanded(any_visible)

    def _build_preset_row(self, preset: presets.Preset) -> Adw.ActionRow:
        row = Adw.ActionRow(title=preset.name, activatable=True)

        icon_path = social_icons.get_icon_path(preset.icon_key)
        if icon_path:
            image = Gtk.Image.new_from_file(str(icon_path))
            image.set_pixel_size(32)
            row.add_prefix(image)
        else:
            row.add_prefix(Adw.Avatar(text=preset.name, show_initials=True, size=32))

        row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        row.connect("activated", self._on_preset_row_activated, preset)
        return row

    def _on_preset_row_activated(self, _row: Adw.ActionRow, preset: presets.Preset) -> None:
        editor = EditorPage(self._nav_view, on_saved=self._on_refresh_list)
        self._nav_view.push(editor)
        editor._on_preset_picked(preset)


_COMPANY_ICON_KEYS = {
    "Amazon": "amazon",
    "Anthropic": "claude",
    "Apple": "apple",
    "Atlassian": "trello",
    "Brave": "brave-search",
    "ByteDance": "tiktok",
    "Canva": "canva",
    "CloudConvert": "cloudconvert",
    "Deezer": "deezer",
    "Dicionário Criativo": "dicionario-criativo",
    "Discord": "discord",
    "Disney": "disney-plus",
    "DuckDuckGo": "duckduckgo",
    "Down For Everyone or Just Me": "down-for-everyone",
    "Ecosia": "ecosia",
    "Evernote": "evernote",
    "Figma": "figma",
    "Focusmate": "focusmate",
    "GetLinkInfo": "getlinkinfo",
    "Globo": "globoplay",
    "Google": "google",
    "Have I Been Pwned": "have-i-been-pwned",
    "LanguageTool": "languagetool",
    "Meta": "facebook",
    "Microsoft": "microsoft-office",
    "Mistral AI": "mistral",
    "Netflix": "netflix",
    "Notion": "notion",
    "Omni Calculator": "omni-calculator",
    "OpenAI": "chatgpt",
    "PDF24": "pdf24-tools",
    "Paramount": "paramount-plus",
    "Perplexity AI": "perplexity",
    "Photopea": "photopea",
    "ProtectedText": "protectedtext",
    "QRCode Monkey": "qrcode-monkey",
    "Reddit": "reddit",
    "Slack": "slack",
    "SoundCloud": "soundcloud",
    "Spotify": "spotify",
    "Startpage": "startpage",
    "Swipefile": "swipefile",
    "Telegram": "telegram-web",
    "TinyWow": "tinywow-pdf",
    "Tidal": "tidal",
    "Twitch": "twitch",
    "UnshortLink": "unshortlink",
    "Warner Bros. Discovery": "max",
    "Wheel of Names": "wheel-of-names",
    "Wormhole": "wormhole",
    "X": "twitter",
    "Yahoo": "yahoo",
    "Answer the Public": "answer-the-public",
    "ME-QR": "me-qr",
    "iLovePDF": "ilovepdf",
    "pdfFiller": "pdffiller",
    "xAI": "grok",
    "DeepSeek": "deepseek",
}

_PACKAGE_ICON_KEYS = {
    "Google Workspace": "google",
    "Microsoft 365": "microsoft-office",
    "YouTube": "youtube2",
    "Inteligência Artificial": "chatgpt",
    "Redes Sociais": "instagram",
}

_COUNTRY_FLAGS = {
    "Brasil": "🇧🇷",
    "Estados Unidos": "🇺🇸",
    "Alemanha": "🇩🇪",
    "Polônia": "🇵🇱",
    "Países Baixos": "🇳🇱",
    "França": "🇫🇷",
    "Reino Unido": "🇬🇧",
    "Europa": "🇪🇺",
    "Argentina": "🇦🇷",
    "Uruguai": "🇺🇾",
    "Paraguai": "🇵🇾",
    "Colômbia": "🇨🇴",
    "Chile": "🇨🇱",
    "México": "🇲🇽",
    "Espanha": "🇪🇸",
    "Internacional": "🌐",
    "Global": "🌐",
}

_KIND_ICON_NAMES = {
    "Mensageiro": "system-users-symbolic",
    "Rede social": "face-smile-big-symbolic",
    "Streaming de vídeo": "multimedia-player-symbolic",
    "Streaming de música": "audio-headphones-symbolic",
    "Inteligência Artificial": "starred-symbolic",
    "Buscador": "system-search-symbolic",
    "Produtividade": "view-list-symbolic",
    "PDF": "text-x-generic-symbolic",
    "Financeiro": "org.gnome.Calculator-symbolic",
    "Utilidade": "preferences-system-symbolic",
    "Conversão e Compartilhamento": "send-to-symbolic",
    "Segurança": "channel-secure-symbolic",
    "Criatividade": "insert-image-symbolic",
    "Computação em Nuvem": "network-server-symbolic",
}

# facets que, na Loja, são seu próprio "modo" (não uma faceta do catálogo comum) e
# sempre aparecem agrupadas por país.
_COUNTRY_GROUPED_KINDS = {
    "marketplace": "Marketplace",
    "news": "Notícias",
}


class StoreWindow(Adw.ApplicationWindow):
    """Loja: janela própria com catálogo de sites prontos, agrupados por Empresa/Tipo/Pacote."""

    def __init__(self, parent: Adw.ApplicationWindow, nav_view: Adw.NavigationView, on_refresh_list):
        super().__init__(
            application=parent.get_application(),
            transient_for=parent,
            default_width=560,
            default_height=760,
            title="Loja",
        )
        self._nav_view = nav_view
        self._on_refresh_list = on_refresh_list
        all_items = store.fetch_catalog()
        special_kinds = set(_COUNTRY_GROUPED_KINDS.values())
        self._catalog_items = [item for item in all_items if item.kind not in special_kinds]
        self._kind_pools = {
            facet_key: [item for item in all_items if item.kind == kind]
            for facet_key, kind in _COUNTRY_GROUPED_KINDS.items()
        }
        self._facet = "company"
        self._group_rows: list[tuple[str, Adw.ExpanderRow, list[tuple[store.StoreItem, Adw.ActionRow]]]] = []
        self._pending_icons: dict[Adw.ExpanderRow, list[tuple[store.StoreItem, Gtk.Box]]] = {}

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        top_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        top_box.set_margin_start(12)
        top_box.set_margin_end(12)
        top_box.set_margin_top(12)

        facet_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER)
        facet_box.add_css_class("linked")
        self._facet_buttons: dict[str, Gtk.ToggleButton] = {}
        first = None
        for key, label in (
            ("company", "Empresa"),
            ("kind", "Tipo"),
            ("package", "Pacote"),
            ("marketplace", "Marketplace"),
            ("news", "Notícias"),
        ):
            toggle = Gtk.ToggleButton(label=label)
            if first is None:
                first = toggle
            else:
                toggle.set_group(first)
            toggle.set_active(key == self._facet)
            toggle.connect("toggled", self._on_facet_toggled, key)
            facet_box.append(toggle)
            self._facet_buttons[key] = toggle
        top_box.append(facet_box)

        self._search_entry = Gtk.SearchEntry(placeholder_text="Buscar por nome…")
        self._search_entry.connect("changed", self._on_search_changed)
        top_box.append(self._search_entry)

        self._page = Adw.PreferencesPage()
        self._page.set_vexpand(True)
        self._current_group: Adw.PreferencesGroup | None = None

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.append(top_box)
        content_box.append(self._page)

        toolbar.set_content(content_box)
        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(toolbar)
        self.set_content(self._toast_overlay)

        self._rebuild_rows()

    def _toast(self, message: str) -> None:
        self._toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def _on_install_package(
        self, _button: Gtk.Button, package_name: str, items: list[store.StoreItem]
    ) -> None:
        sub_apps = []
        for item in items:
            icon_path = store.save_icon_to_temp(item)
            sub_apps.append(
                {"name": item.name, "url": item.url, "icon_source": str(icon_path) if icon_path else None}
            )

        package_icon = social_icons.get_icon_path(_PACKAGE_ICON_KEYS.get(package_name))
        if package_icon is None:
            package_icon = store.save_icon_to_temp(items[0])
        if package_icon is None:
            self._toast(f"Não foi possível definir um ícone para {package_name}.")
            return

        try:
            entries.create_package(package_name, sub_apps, package_icon)
        except ValueError as error:
            self._toast(f"Erro ao instalar pacote: {error}")
            return

        self._on_refresh_list()
        self._toast(f"Pacote “{package_name}” instalado com {len(items)} apps.")

    def _on_facet_toggled(self, toggle: Gtk.ToggleButton, key: str) -> None:
        if toggle.get_active():
            self._facet = key
            self._rebuild_rows()

    def _rebuild_rows(self) -> None:
        if self._current_group is not None:
            self._page.remove(self._current_group)
            self._current_group = None
        self._group_rows.clear()
        self._pending_icons.clear()

        is_special = self._facet in _COUNTRY_GROUPED_KINDS
        items_pool = self._kind_pools[self._facet] if is_special else self._catalog_items
        group_key = "country" if is_special else self._facet

        if not items_pool:
            status = Adw.StatusPage(
                icon_name="org.gnome.Software-symbolic",
                title="Nada por aqui ainda",
                description="Verifique o catálogo local ou a conexão com a internet.",
            )
            group = Adw.PreferencesGroup()
            group.add(status)
            self._page.add(group)
            self._current_group = group
            return

        grouped = store.group_by(items_pool, group_key)
        group = Adw.PreferencesGroup()
        for key, items in grouped.items():
            expander = Adw.ExpanderRow(title=key, subtitle=f"{len(items)} sites")
            expander.add_prefix(self._group_icon_widget(key))
            if group_key == "package" and key != "Apps independentes":
                install_button = Gtk.Button(
                    label="Instalar pacote completo", valign=Gtk.Align.CENTER
                )
                install_button.add_css_class("flat")
                install_button.connect("clicked", self._on_install_package, key, items)
                expander.add_suffix(install_button)
            rows = []
            pending_icons = []
            for item in items:
                row, icon_slot = self._build_item_row(item)
                expander.add_row(row)
                rows.append((item, row))
                pending_icons.append((item, icon_slot))
            self._pending_icons[expander] = pending_icons
            expander.connect("notify::expanded", self._on_group_expanded)
            group.add(expander)
            self._group_rows.append((key, expander, rows))
        self._page.add(group)
        self._current_group = group

        self._apply_search()

    def _on_group_expanded(self, expander: Adw.ExpanderRow, _pspec) -> None:
        """Só busca/decodifica os ícones de um grupo (base64 -> PNG em disco) na primeira
        vez que ele é expandido — evita fazer isso pra todos os itens do catálogo (incl.
        grupos que o usuário nunca abre) toda vez que a Loja é aberta ou a aba é trocada."""
        if not expander.get_expanded():
            return
        pending = self._pending_icons.pop(expander, None)
        if not pending:
            return
        for item, icon_slot in pending:
            placeholder = icon_slot.get_first_child()
            if placeholder is not None:
                icon_slot.remove(placeholder)
            icon_path = store.save_icon_to_temp(item)
            if icon_path:
                image = Gtk.Image.new_from_file(str(icon_path))
                image.set_pixel_size(32)
                icon_slot.append(image)
            else:
                icon_slot.append(Adw.Avatar(text=item.name, show_initials=True, size=32))

    def _group_icon_widget(self, key: str) -> Gtk.Widget:
        if self._facet == "company":
            icon_path = social_icons.get_icon_path(_COMPANY_ICON_KEYS.get(key))
            if icon_path:
                image = Gtk.Image.new_from_file(str(icon_path))
                image.set_pixel_size(28)
                return image
            return Adw.Avatar(text=key, show_initials=True, size=28)

        if self._facet == "package":
            icon_path = social_icons.get_icon_path(_PACKAGE_ICON_KEYS.get(key))
            if icon_path:
                image = Gtk.Image.new_from_file(str(icon_path))
                image.set_pixel_size(28)
                return image
            return Gtk.Image.new_from_icon_name("view-grid-symbolic")

        if self._facet == "country" or self._facet in _COUNTRY_GROUPED_KINDS:
            flag = _COUNTRY_FLAGS.get(key, "🌐")
            label = Gtk.Label(label=flag)
            label.set_markup(f'<span font_desc="24">{GLib.markup_escape_text(flag)}</span>')
            return label

        icon_name = _KIND_ICON_NAMES.get(key, "view-grid-symbolic")
        image = Gtk.Image.new_from_icon_name(icon_name)
        image.set_pixel_size(24)
        return image

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        self._apply_search()

    def _apply_search(self) -> None:
        query = _fold(self._search_entry.get_text().strip())

        if not query:
            for _key, expander, rows in self._group_rows:
                expander.set_visible(True)
                expander.set_expanded(False)
                for _item, row in rows:
                    row.set_visible(True)
            return

        for key, expander, rows in self._group_rows:
            group_matches = query in _fold(key)
            any_visible = False
            for item, row in rows:
                visible = group_matches or query in _fold(item.name)
                row.set_visible(visible)
                any_visible = any_visible or visible
            expander.set_visible(any_visible)
            expander.set_expanded(any_visible)

    def _build_item_row(self, item: store.StoreItem) -> tuple[Adw.ActionRow, Gtk.Box]:
        """Monta a linha com um placeholder leve (Avatar com iniciais, sem tocar disco).
        O ícone real (decodificado do base64 do catálogo) só é carregado quando o grupo
        é expandido — ver `_on_group_expanded`."""
        row = Adw.ActionRow(title=item.name, activatable=True)

        icon_slot = Gtk.Box()
        icon_slot.append(Adw.Avatar(text=item.name, show_initials=True, size=32))
        row.add_prefix(icon_slot)

        row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        row.connect("activated", self._on_item_row_activated, item)
        return row, icon_slot

    def _on_item_row_activated(self, _row: Adw.ActionRow, item: store.StoreItem) -> None:
        editor = EditorPage(self._nav_view, on_saved=self._on_refresh_list)
        self._nav_view.push(editor)
        editor._on_store_item_picked(item)
        self.close()


class HelpWindow(Adw.ApplicationWindow):
    """Manual de uso do Casca, renderizado a partir do help.html incluído no pacote."""

    def __init__(self, parent: Adw.ApplicationWindow):
        super().__init__(
            application=parent.get_application(),
            transient_for=parent,
            default_width=780,
            default_height=760,
            title="Manual do Casca",
        )

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        help_path = Path(__file__).parent / "data" / "help.html"
        try:
            gi.require_version("WebKit", "6.0")
            from gi.repository import WebKit

            web_view = WebKit.WebView()
            web_view.load_uri(f"file://{help_path}")
            toolbar.set_content(web_view)
        except (ValueError, ImportError):
            status = Adw.StatusPage(
                icon_name="help-about-symbolic",
                title="Não foi possível abrir o manual embutido",
                description=str(help_path),
            )
            toolbar.set_content(status)

        self.set_content(toolbar)


class ImportSelectionDialog(Adw.Dialog):
    """Lista os apps encontrados num JSON de importação com um interruptor por item —
    nada é importado sem seleção explícita."""

    def __init__(self, app_entries: list[dict], on_confirm):
        super().__init__(title="Escolher o que importar", content_width=440, content_height=560)
        self._app_entries = app_entries
        self._on_confirm = on_confirm
        self._switches: list[Adw.SwitchRow] = []

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(
            title=f"{len(app_entries)} site(s) encontrados",
            description="Desmarque o que não quiser importar.",
        )
        for entry in app_entries:
            name = entry.get("name") or "(sem nome)"
            url = entry.get("url") or ""
            row = Adw.SwitchRow(title=name, subtitle=url, active=True)
            group.add(row)
            self._switches.append(row)
        page.add(group)

        actions = Adw.PreferencesGroup()
        import_button = Gtk.Button(label="Importar selecionados")
        import_button.add_css_class("suggested-action")
        import_button.add_css_class("pill")
        import_button.set_halign(Gtk.Align.CENTER)
        import_button.set_margin_top(12)
        import_button.connect("clicked", self._on_confirm_clicked)
        actions.add(import_button)
        page.add(actions)

        toolbar.set_content(page)
        self.set_child(toolbar)

    def _on_confirm_clicked(self, _button: Gtk.Button) -> None:
        selected = {index for index, row in enumerate(self._switches) if row.get_active()}
        self.close()
        self._on_confirm(self._app_entries, selected)


class ListPage(Adw.NavigationPage):
    """Página com a lista de web apps já criados."""

    def __init__(self, nav_view: Adw.NavigationView):
        super().__init__(title="Casca")
        self._nav_view = nav_view

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()

        app_icon = Gtk.Image.new_from_icon_name("io.github.oliverhubtech_source.Casca")
        app_icon.set_pixel_size(20)
        header.pack_start(app_icon)

        menu = Gio.Menu()
        menu.append("Manual de uso", "page.help")
        menu.append("Sobre o Casca", "page.about")
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text="Menu")
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)
        toolbar.add_top_bar(header)

        actions = Gio.SimpleActionGroup()
        for name, handler in (
            ("help", self._on_open_help),
            ("about", self._on_open_about),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", handler)
            actions.add_action(action)
        self.insert_action_group("page", actions)

        self._page = Adw.PreferencesPage()
        self._groups: list[Adw.PreferencesGroup] = []
        toolbar.set_content(self._page)

        bottom_bar = Gtk.CenterBox(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_bar.set_margin_top(12)
        bottom_bar.set_margin_bottom(12)
        bottom_bar.set_margin_start(12)
        bottom_bar.set_margin_end(12)

        store_button = Gtk.Button(icon_name="org.gnome.Software-symbolic", tooltip_text="Loja")
        store_button.add_css_class("pill")
        store_button.connect("clicked", self._on_open_store_page)
        bottom_bar.set_start_widget(store_button)

        create_button = Gtk.Button(tooltip_text="Criar um novo web app")
        create_button.set_child(Adw.ButtonContent(icon_name="list-add-symbolic", label="Criar"))
        create_button.add_css_class("suggested-action")
        create_button.add_css_class("pill")
        create_button.connect("clicked", self._on_add)
        bottom_bar.set_center_widget(create_button)

        import_export_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        import_export_box.add_css_class("linked")

        import_button = Gtk.Button(icon_name="document-open-symbolic", tooltip_text="Importar apps")
        import_button.connect("clicked", self._on_import)
        import_export_box.append(import_button)

        export_button = Gtk.Button(icon_name="document-save-symbolic", tooltip_text="Exportar apps")
        export_button.connect("clicked", self._on_export)
        import_export_box.append(export_button)

        bottom_bar.set_end_widget(import_export_box)
        toolbar.add_bottom_bar(bottom_bar)

        self.set_child(toolbar)

        self.refresh()

    def _on_add(self, *_args) -> None:
        editor = EditorPage(self._nav_view, on_saved=self.refresh)
        self._nav_view.push(editor)

    def _on_open_store_page(self, *_args) -> None:
        window = StoreWindow(self.get_ancestor(Gtk.Window), self._nav_view, on_refresh_list=self.refresh)
        window.present()

    def _on_open_help(self, *_args) -> None:
        window = HelpWindow(self.get_ancestor(Gtk.Window))
        window.present()

    def _on_open_about(self, *_args) -> None:
        about = Adw.AboutDialog(
            application_name="Casca",
            application_icon="io.github.oliverhubtech_source.Casca",
            version="1.0",
            developer_name="OliverHub",
            comments="Transforma qualquer site num app do GNOME.",
        )
        about.present(self)

    def _toast(self, message: str) -> None:
        root = self.get_ancestor(Gtk.Window)
        if isinstance(root, CascaWindow):
            root.toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def _on_export(self, *_args) -> None:
        if not entries.list_apps():
            self._toast("Nenhum app criado ainda para exportar.")
            return
        dialog = Gtk.FileDialog(title="Exportar apps", initial_name="casca-apps.json")
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON")
        filter_json.add_pattern("*.json")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_json)
        dialog.set_filters(filters)
        dialog.save(self.get_ancestor(Gtk.Window), None, self._on_export_chosen)

    def _on_export_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return
        if gfile is None:
            return
        path = Path(gfile.get_path())
        if path.suffix != ".json":
            path = path.with_suffix(".json")
        try:
            count = entries.export_apps(path)
        except OSError as error:
            self._toast(f"Erro ao exportar: {error}")
            return
        self._toast(f"{count} app(s) exportado(s) para {path.name}.")

    def _on_import(self, *_args) -> None:
        dialog = Adw.AlertDialog(
            heading="Importar de onde?",
            body='Escolha um arquivo .json local ou uma URL (ex.: um link "raw" do GitHub).',
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("url", "De uma URL")
        dialog.add_response("file", "Arquivo local")
        dialog.set_response_appearance("file", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("file")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_import_source_chosen)
        dialog.present(self)

    def _on_import_source_chosen(self, _dialog: Adw.AlertDialog, response: str) -> None:
        if response == "file":
            self._on_import_pick_file()
        elif response == "url":
            self._on_import_pick_url()

    def _on_import_pick_file(self) -> None:
        dialog = Gtk.FileDialog(title="Importar apps")
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON")
        filter_json.add_pattern("*.json")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_json)
        dialog.set_filters(filters)
        dialog.open(self.get_ancestor(Gtk.Window), None, self._on_import_file_chosen)

    def _on_import_file_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error:
            return
        if gfile is None:
            return
        try:
            data = Path(gfile.get_path()).read_bytes()
        except OSError as error:
            self._toast(f"Erro ao ler o arquivo: {error}")
            return
        self._open_import_selection(data)

    def _on_import_pick_url(self) -> None:
        dialog = Adw.AlertDialog(
            heading="Importar de uma URL",
            body='Cole o link "raw" do arquivo JSON (ex.: de um repositório no GitHub).',
        )
        entry = Adw.EntryRow(title="URL")
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("fetch", "Buscar")
        dialog.set_response_appearance("fetch", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("fetch")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_import_url_response, entry)
        dialog.present(self)

    def _on_import_url_response(self, _dialog: Adw.AlertDialog, response: str, entry: Adw.EntryRow) -> None:
        if response != "fetch":
            return
        url = entry.get_text().strip()
        if not url:
            self._toast("Informe uma URL.")
            return
        self._toast("Buscando arquivo…")
        threading.Thread(target=self._fetch_import_url_worker, args=(url,), daemon=True).start()

    def _fetch_import_url_worker(self, url: str) -> None:
        try:
            data = entries.fetch_import_payload(url)
        except ValueError as error:
            GLib.idle_add(self._toast, f"Erro ao baixar: {error}")
            return
        GLib.idle_add(self._open_import_selection, data)

    def _open_import_selection(self, data: bytes) -> bool:
        try:
            app_entries = entries.parse_import_candidates(data)
        except ValueError as error:
            self._toast(f"Erro ao importar: {error}")
            return False
        if not app_entries:
            self._toast("Nenhum app encontrado no arquivo.")
            return False
        dialog = ImportSelectionDialog(app_entries, on_confirm=self._on_import_selection_confirmed)
        dialog.present(self)
        return False

    def _on_import_selection_confirmed(self, app_entries: list[dict], selected_indices: set[int]) -> None:
        if not selected_indices:
            self._toast("Nada selecionado para importar.")
            return
        result = entries.import_selected(app_entries, selected_indices)
        self.refresh()
        if result.failures:
            self._show_import_errors(result)
        else:
            self._toast(f"{len(result.created)} app(s) importado(s).")

    def _show_import_errors(self, result: entries.ImportResult) -> None:
        lines = "\n".join(f"• {failure.name}: {failure.reason}" for failure in result.failures)
        dialog = Adw.AlertDialog(
            heading=f"{len(result.created)} importado(s), {len(result.failures)} com erro",
            body=f"Revise e ajuste manualmente pelo botão “Criar”:\n\n{lines}",
        )
        dialog.add_response("ok", "Entendi")
        dialog.present(self)

    def refresh(self) -> None:
        for group in self._groups:
            self._page.remove(group)
        self._groups.clear()

        apps = entries.list_apps()
        packages = entries.list_packages()

        if not apps and not packages:
            status = Adw.StatusPage(
                icon_name="io.github.oliverhubtech_source.Casca",
                title="Nenhum web app ainda",
                description="Toque em “Criar de predefinido” ou “Criar novo webapp” para começar.",
            )
            group = Adw.PreferencesGroup()
            group.add(status)
            self._page.add(group)
            self._groups.append(group)
            return

        if apps:
            group = Adw.PreferencesGroup(title="Meus web apps")
            for app in apps:
                row = Adw.ActionRow(title=app.name, subtitle=app.url)
                row.add_prefix(_row_leading_widget(app.icon_path))

                edit_button = Gtk.Button(icon_name="document-edit-symbolic", valign=Gtk.Align.CENTER)
                edit_button.add_css_class("flat")
                edit_button.connect("clicked", self._on_edit, app)

                delete_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
                delete_button.add_css_class("flat")
                delete_button.connect("clicked", self._on_delete, app)

                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                box.append(edit_button)
                box.append(delete_button)
                row.add_suffix(box)
                group.add(row)
            self._page.add(group)
            self._groups.append(group)

        if packages:
            pkg_group = Adw.PreferencesGroup(title="Pacotes instalados")
            for package in packages:
                row = Adw.ActionRow(
                    title=package.name, subtitle=", ".join(package.app_names)
                )
                row.add_prefix(_row_leading_widget(package.icon_path))

                delete_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
                delete_button.add_css_class("flat")
                delete_button.connect("clicked", self._on_delete_package, package)
                row.add_suffix(delete_button)
                pkg_group.add(row)
            self._page.add(pkg_group)
            self._groups.append(pkg_group)

    def _on_edit(self, _button: Gtk.Button, app: entries.WebApp) -> None:
        editor = EditorPage(self._nav_view, on_saved=self.refresh, existing=app)
        self._nav_view.push(editor)

    def _on_delete(self, _button: Gtk.Button, app: entries.WebApp) -> None:
        dialog = Adw.AlertDialog(
            heading=f"Excluir “{app.name}”?",
            body="O atalho será removido do menu de aplicativos e da área de trabalho, se existir.",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("delete", "Excluir")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_delete_response, app)
        dialog.present(self)

    def _on_delete_response(self, _dialog: Adw.AlertDialog, response: str, app: entries.WebApp) -> None:
        if response == "delete":
            entries.delete_app(app.slug)
            self.refresh()

    def _on_delete_package(self, _button: Gtk.Button, package: entries.PackageInfo) -> None:
        dialog = Adw.AlertDialog(
            heading=f"Excluir pacote “{package.name}”?",
            body=f"Remove o atalho e os {len(package.app_names)} apps dentro dele ({', '.join(package.app_names)}).",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("delete", "Excluir")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_delete_package_response, package)
        dialog.present(self)

    def _on_delete_package_response(
        self, _dialog: Adw.AlertDialog, response: str, package: entries.PackageInfo
    ) -> None:
        if response == "delete":
            entries.delete_package(package.slug)
            self.refresh()


class CascaWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application):
        super().__init__(application=application, title="Casca", default_width=480, default_height=640)

        self.toast_overlay = Adw.ToastOverlay()
        nav_view = Adw.NavigationView()
        nav_view.push(ListPage(nav_view))
        self.toast_overlay.set_child(nav_view)
        self.set_content(self.toast_overlay)
