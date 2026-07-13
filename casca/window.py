"""Casca's UI: list of web apps and the creation/edit form."""

import itertools
import threading
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango

_header_class_counter = itertools.count()

from . import __version__, browsers, devices, entries, help_content, icons, presets, profiles, social_icons, store, updater
from .fileutils import has_dangerous_scheme
from .headerbar_css import build_header_css
from .i18n import _, ngettext


def _fold(text: str) -> str:
    """Normalize text for search: lowercase and without accents."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def _row_icon(path_str: str) -> Gtk.Widget:
    if path_str and Path(path_str).exists():
        image = Gtk.Image.new_from_file(path_str)
    else:
        image = Gtk.Image.new_from_icon_name("web-browser-symbolic")
    image.set_pixel_size(32)
    return image


def _color_bar(rgb: tuple[int, int, int]) -> Gtk.Widget:
    """Thin vertical stripe painted with the app icon's dominant color."""
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
    """Color stripe + icon, to use as an Adw.ActionRow prefix."""
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
    """Grid with the brand icons bundled with Casca, for use on custom sites."""

    def __init__(self, on_pick):
        super().__init__(title=_("Choose icon"), content_width=480, content_height=600)

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
    """Searches for the site's icon across several sources and shows the results in a grid."""

    def __init__(self, url: str, on_pick):
        super().__init__(title=_("Icons found"), content_width=460, content_height=420)
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
        box.append(Gtk.Label(label=_("Searching for icons online…")))
        self._toolbar.set_content(box)

    def _search_worker(self) -> None:
        results = icons.search_icons(self._url)
        GLib.idle_add(self._show_results, results)

    def _show_results(self, results: list[tuple[str, bytes]]) -> bool:
        if not results:
            status = Adw.StatusPage(
                icon_name="dialog-warning-symbolic",
                title=_("No icon found"),
                description=_("Try choosing an image from your computer or the gallery."),
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
    """Web app creation/edit form."""

    def __init__(self, nav_view: Adw.NavigationView, on_saved, existing: entries.WebApp | None = None):
        super().__init__(title=_("Edit app") if existing else _("New app"))
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

        site_group = Adw.PreferencesGroup(title=_("Site"))
        self._name_row = Adw.EntryRow(title=_("App name"))
        self._url_row = Adw.EntryRow(title=_("Address (URL)"))
        site_group.add(self._name_row)
        site_group.add(self._url_row)

        self._environments = entries.list_environments()
        self._environment_row = Adw.ComboRow(title=_("Environment"))
        environment_labels = Gtk.StringList()
        environment_labels.append(_("Default"))
        for env in self._environments:
            environment_labels.append(env.name)
        self._environment_row.set_model(environment_labels)
        self._environment_row.connect("notify::selected", self._on_environment_changed)
        site_group.add(self._environment_row)
        page.add(site_group)

        browser_group = Adw.PreferencesGroup(title=_("Browser"))

        self._custom_browser_expander = Adw.ExpanderRow(
            title=_("Use a custom browser"),
            subtitle=_("If disabled, opens in Casca's own window."),
        )
        self._custom_browser_expander.set_show_enable_switch(True)
        self._custom_browser_expander.set_enable_expansion(False)
        self._custom_browser_expander.connect("notify::enable-expansion", self._on_browser_changed)

        self._browser_row = Adw.ComboRow(title=_("Open with"))
        labels = Gtk.StringList()
        for browser in self._detected_browsers:
            labels.append(browser.label)
        self._browser_row.set_model(labels)
        if not self._detected_browsers:
            self._browser_row.set_sensitive(False)
            self._custom_browser_expander.set_subtitle(_("No compatible browser was found on the system."))
        if browsers.in_flatpak():
            # Sandboxed, Casca doesn't detect/offer external browsers (see
            # browsers.py) — the only real option is already its own window, so the
            # toggle is disabled instead of showing a list with a single option.
            self._custom_browser_expander.set_sensitive(False)
            self._custom_browser_expander.set_subtitle(
                _("Not available in the Flatpak version — use the local install for external browsers.")
            )
        self._browser_row.connect("notify::selected", self._on_browser_changed)
        self._custom_browser_expander.add_row(self._browser_row)
        self._custom_browser_expander.add_suffix(
            self._help_button("navegador", _("Learn more about custom browsers"))
        )

        self._profile_row = Adw.ComboRow(title=_("Browser account"))
        self._profile_options: list[str | None] = [None]
        self._custom_browser_expander.add_row(self._profile_row)

        browser_group.add(self._custom_browser_expander)

        self._mobile_expander = Adw.ExpanderRow(
            title=_("Open in mobile mode"),
            subtitle=_("Uses the identification and window of a phone or tablet."),
        )
        self._mobile_expander.set_show_enable_switch(True)
        self._mobile_expander.set_enable_expansion(False)
        self._mobile_expander.connect("notify::enable-expansion", self._on_mobile_toggled)

        self._device_row = Adw.ComboRow(title=_("Device"))
        device_labels = Gtk.StringList()
        for device in devices.DEVICES:
            device_labels.append(device.label)
        self._device_row.set_model(device_labels)
        self._mobile_expander.add_row(self._device_row)
        self._mobile_expander.add_suffix(self._help_button("mobile", _("Learn more about mobile mode")))

        browser_group.add(self._mobile_expander)
        page.add(browser_group)
        self._update_mobile_switch_availability()
        self._update_profile_options()

        resolution_group = Adw.PreferencesGroup()
        self._resolution_expander = Adw.ExpanderRow(
            title=_("Customize window resolution"),
            subtitle=_("If disabled, uses the browser's default size."),
        )
        self._resolution_expander.set_show_enable_switch(True)
        self._resolution_expander.set_enable_expansion(False)

        self._resolution_row = Adw.ComboRow(title=_("Window size"))
        resolution_modes = Gtk.StringList()
        for mode_label in (_("By device"), _("Default size"), _("Custom")):
            resolution_modes.append(mode_label)
        self._resolution_row.set_model(resolution_modes)
        self._resolution_row.connect("notify::selected", self._on_resolution_mode_changed)
        self._resolution_expander.add_row(self._resolution_row)

        self._resolution_device_row = Adw.ComboRow(title=_("Device"))
        self._resolution_device_row.set_model(device_labels)
        self._resolution_expander.add_row(self._resolution_device_row)

        self._resolution_preset_row = Adw.ComboRow(title=_("Size"))
        preset_sizes = Gtk.StringList()
        for size in devices.STANDARD_SIZES:
            preset_sizes.append(size.label)
        self._resolution_preset_row.set_model(preset_sizes)
        self._resolution_expander.add_row(self._resolution_preset_row)

        self._resolution_width_row = Adw.SpinRow(
            title=_("Width"), adjustment=Gtk.Adjustment(lower=200, upper=4000, step_increment=10, value=1024)
        )
        self._resolution_height_row = Adw.SpinRow(
            title=_("Height"), adjustment=Gtk.Adjustment(lower=200, upper=4000, step_increment=10, value=768)
        )
        self._resolution_expander.add_row(self._resolution_width_row)
        self._resolution_expander.add_row(self._resolution_height_row)
        self._resolution_expander.add_suffix(
            self._help_button("resolucao", _("Learn more about window resolution"))
        )

        resolution_group.add(self._resolution_expander)
        page.add(resolution_group)
        self._update_resolution_visibility()

        icon_group = Adw.PreferencesGroup()
        self._icon_expander = Adw.ExpanderRow(
            title=_("Customize icon and shortcut"),
            subtitle=_(
                "If disabled, the icon is fetched automatically and no Desktop shortcut is created."
            ),
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
        search_button = Gtk.Button(label=_("Search online"))
        search_button.connect("clicked", self._on_search_icons)
        choose_button = Gtk.Button(label=_("From computer"))
        choose_button.connect("clicked", self._on_choose_icon)
        gallery_button = Gtk.Button(label=_("From gallery"))
        gallery_button.connect("clicked", self._on_open_gallery)
        button_box.append(search_button)
        button_box.append(choose_button)
        button_box.append(gallery_button)
        icon_box.append(button_box)

        self._icon_expander.add_row(icon_box)

        self._desktop_switch_row = Adw.SwitchRow(title=_("Also create on the Desktop"))
        self._icon_expander.add_row(self._desktop_switch_row)
        self._icon_expander.add_suffix(
            self._help_button("icone", _("Learn more about icons and shortcuts"))
        )

        icon_group.add(self._icon_expander)
        page.add(icon_group)

        actions_group = Adw.PreferencesGroup()
        self._save_button = Gtk.Button(label=_("Create app"))
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

    def _selected_environment(self) -> str:
        index = self._environment_row.get_selected()
        if index <= 0 or index > len(self._environments):
            return entries.DEFAULT_ENVIRONMENT
        return self._environments[index - 1].slug

    def _on_environment_changed(self, *_args) -> None:
        """Creating an app inside an environment prefills the editor with that
        environment's defaults; editing an existing app never gets overwritten."""
        if self._existing is not None:
            return
        index = self._environment_row.get_selected()
        if index <= 0 or index > len(self._environments):
            return
        defaults = self._environments[index - 1].defaults or {}

        browser_key = defaults.get("browser_key")
        if browser_key:
            self._custom_browser_expander.set_enable_expansion(browser_key != "webkit:casca")
            for i, browser in enumerate(self._detected_browsers):
                if browser.key == browser_key:
                    self._browser_row.set_selected(i)
                    break
        self._update_profile_options()
        browser_profile = defaults.get("browser_profile")
        if browser_profile and browser_profile in self._profile_options:
            self._profile_row.set_selected(self._profile_options.index(browser_profile))

        self._update_mobile_switch_availability()
        self._mobile_expander.set_enable_expansion(bool(defaults.get("mobile")))
        device_key = defaults.get("device_key")
        if device_key:
            for i, device in enumerate(devices.DEVICES):
                if device.key == device_key:
                    self._device_row.set_selected(i)
                    break

        width, height = defaults.get("width"), defaults.get("height")
        if width and height:
            self._resolution_expander.set_enable_expansion(True)
            self._resolution_row.set_selected(2)
            self._resolution_width_row.set_value(width)
            self._resolution_height_row.set_value(height)
            self._update_resolution_visibility()

    def _load_existing(self, app: entries.WebApp) -> None:
        self.set_title(_("Edit app"))
        self._save_button.set_label(_("Save changes"))
        self._name_row.set_text(app.name)
        self._url_row.set_text(app.url)
        for index, env in enumerate(self._environments):
            if env.slug == app.environment:
                self._environment_row.set_selected(index + 1)
                break
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
                _("%(browser)s doesn't support mobile mode.") % {"browser": browser.label}
                if browser
                else _("Choose a browser.")
            )
        else:
            self._mobile_expander.set_subtitle(_("Uses the identification and window of a phone or tablet."))

    def _update_profile_options(self) -> None:
        browser = self._current_browser()
        found = profiles.list_profiles(browser) if browser and browser.supports_account_profile else []

        labels = Gtk.StringList()
        labels.append(_("Isolated profile (new, no login)"))
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
            self._toast(_("Enter the URL before searching for the icon."))
            return
        data = icons.fetch_favicon(url)
        if not data:
            self._toast(_("Could not fetch the icon automatically."))
            return
        temp_path = Path(GLib.get_tmp_dir()) / "casca-favicon-preview.png"
        temp_path.write_bytes(data)
        self._auto_icon_path = temp_path
        self._picked_icon_path = None
        self._set_icon_preview(str(temp_path))

    def _on_search_icons(self, _button: Gtk.Button) -> None:
        url = self._url_row.get_text().strip()
        if not url:
            self._toast(_("Enter the URL before searching for the icon."))
            return
        dialog = IconSearchDialog(url, on_pick=self._on_search_icon_picked)
        dialog.present(self)

    def _on_search_icon_picked(self, path: Path) -> None:
        self._picked_icon_path = path
        self._auto_icon_path = None
        self._set_icon_preview(str(path))

    def _on_choose_icon(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog(title=_("Choose icon image"))
        filter_images = Gtk.FileFilter()
        filter_images.set_name(_("Images"))
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

    def _help_button(self, anchor: str, tooltip: str) -> Gtk.Button:
        """Small "i" button: hovering shows a short tooltip, clicking opens the
        manual scrolled to the matching section — a bit of inline, interactive docs."""
        button = Gtk.Button(icon_name="help-about-symbolic", valign=Gtk.Align.CENTER)
        button.add_css_class("flat")
        button.set_tooltip_text(tooltip)
        button.connect("clicked", self._on_help_button_clicked, anchor)
        return button

    def _on_help_button_clicked(self, _button: Gtk.Button, anchor: str) -> None:
        window = HelpWindow(self.get_ancestor(Gtk.Window), anchor=anchor)
        window.present()

    def _on_save(self, _button: Gtk.Button) -> None:
        name = self._name_row.get_text().strip()
        url = self._url_row.get_text().strip()

        if not name or not url:
            self._toast(_("Fill in the site's name and URL."))
            return
        if has_dangerous_scheme(url):
            self._toast(_("Use an http:// or https:// address."))
            return
        if "://" not in url:
            url = f"https://{url}"
        if urlparse(url).scheme not in ("http", "https"):
            self._toast(_("Use an http:// or https:// address."))
            return

        if self._custom_browser_expander.get_enable_expansion():
            selected = self._browser_row.get_selected()
            if selected == Gtk.INVALID_LIST_POSITION or not self._detected_browsers:
                self._toast(_("Choose a browser."))
                return
            browser_key = self._detected_browsers[selected].key
            profile_selected = self._profile_row.get_selected()
            browser_profile = (
                self._profile_options[profile_selected] if profile_selected != Gtk.INVALID_LIST_POSITION else None
            )
        else:
            webkit_browser = next((b for b in self._detected_browsers if b.key == "webkit:casca"), None)
            if webkit_browser is None:
                self._toast(_("Casca's own window isn't available. Enable 'Use a custom browser'."))
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
            # customization disabled: ignore the manual choice, keep whatever was
            # already resolved automatically (e.g. a preset's icon), and no shortcut.
            desktop_shortcut = False
            icon_source = self._auto_icon_path

        environment = self._selected_environment()
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
                    environment,
                )
            else:
                if icon_source is None:
                    data = icons.fetch_favicon(url)
                    slug_guess = entries.slugify(name)
                    icon_source = icons.save_icon_from_bytes(data, slug_guess) if data else None
                if icon_source is None:
                    self._toast(_("Could not set an icon. Choose an image manually."))
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
                    environment,
                )
        except (ValueError, KeyError, OSError) as error:
            self._toast(_("Error saving: %(error)s") % {"error": error})
            return

        self._on_saved()
        self._nav_view.pop()


def _environment_combo(preselect_slug: str | None = None) -> tuple[Adw.ComboRow, list["entries.EnvironmentInfo"]]:
    """ComboRow "Environment" with Default + created environments, shared by the
    app, package and (future) editors."""
    environments = entries.list_environments()
    row = Adw.ComboRow(title=_("Environment"))
    labels = Gtk.StringList()
    labels.append(_("Default"))
    for env in environments:
        labels.append(env.name)
    row.set_model(labels)
    if preselect_slug:
        for index, env in enumerate(environments):
            if env.slug == preselect_slug:
                row.set_selected(index + 1)
                break
    return row, environments


def _combo_environment_slug(row: Adw.ComboRow, environments: list["entries.EnvironmentInfo"]) -> str:
    index = row.get_selected()
    if index <= 0 or index > len(environments):
        return entries.DEFAULT_ENVIRONMENT
    return environments[index - 1].slug


class StoreItemPickerDialog(Adw.Dialog):
    """Searchable list of the Store catalog (name + company, no icons decoded)
    to pick a site for a package."""

    def __init__(self, on_pick):
        super().__init__(title=_("Add from the Store"), content_width=440, content_height=560)
        self._on_pick = on_pick
        self._entries: list[tuple[store.StoreItem, Adw.ActionRow]] = []

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_bottom(12)

        search = Gtk.SearchEntry(placeholder_text=_("Search by name…"))
        search.connect("changed", self._on_search_changed)
        box.append(search)

        scrolled = Gtk.ScrolledWindow(vexpand=True)
        listbox = Gtk.ListBox()
        listbox.add_css_class("boxed-list")
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        for item in store.fetch_catalog():
            row = Adw.ActionRow(title=item.name, subtitle=item.company, activatable=True)
            row.connect("activated", self._on_row_activated, item)
            listbox.append(row)
            self._entries.append((item, row))
        scrolled.set_child(listbox)
        box.append(scrolled)

        toolbar.set_content(box)
        self.set_child(toolbar)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        query = _fold(entry.get_text().strip())
        for item, row in self._entries:
            row.set_visible(not query or query in _fold(item.name) or query in _fold(item.company))

    def _on_row_activated(self, _row: Adw.ActionRow, item: store.StoreItem) -> None:
        self._on_pick(item)
        self.close()


class CustomSiteDialog(Adw.Dialog):
    """Name + URL form to add a custom site to a package."""

    def __init__(self, on_confirm):
        super().__init__(title=_("Add site"), content_width=420, content_height=300)
        self._on_confirm = on_confirm

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()
        self._name_row = Adw.EntryRow(title=_("App name"))
        self._url_row = Adw.EntryRow(title=_("Address (URL)"))
        group.add(self._name_row)
        group.add(self._url_row)
        page.add(group)

        actions = Adw.PreferencesGroup()
        add_button = Gtk.Button(label=_("Add"))
        add_button.add_css_class("suggested-action")
        add_button.add_css_class("pill")
        add_button.set_halign(Gtk.Align.CENTER)
        add_button.connect("clicked", self._on_add_clicked)
        actions.add(add_button)
        page.add(actions)

        toolbar.set_content(page)
        self.set_child(toolbar)
        self._error_label = Gtk.Label()
        self._error_label.add_css_class("error")
        actions.add(self._error_label)

    def _on_add_clicked(self, _button: Gtk.Button) -> None:
        name = self._name_row.get_text().strip()
        url = self._url_row.get_text().strip()
        if not name or not url:
            self._error_label.set_label(_("Fill in the site's name and URL."))
            return
        if has_dangerous_scheme(url):
            self._error_label.set_label(_("Use an http:// or https:// address."))
            return
        if "://" not in url:
            url = f"https://{url}"
        if urlparse(url).scheme not in ("http", "https"):
            self._error_label.set_label(_("Use an http:// or https:// address."))
            return
        self._on_confirm(name, url)
        self.close()


class PackageEditorPage(Adw.NavigationPage):
    """Creates or edits a package: one launcher in the menu that opens a window
    with several apps inside. Contents come from the Store catalog or custom
    name+URL sites — independent copies, never linked to installed apps."""

    def __init__(self, nav_view: Adw.NavigationView, on_saved, existing: entries.PackageInfo | None = None):
        super().__init__(title=_("Edit package") if existing else _("New package"))
        self._nav_view = nav_view
        self._on_saved = on_saved
        self._existing = existing
        self._picked_icon_path: Path | None = None
        # each entry: {"name": str, "url": str, "icon_source": str | None}
        self._sub_apps: list[dict] = []
        self._sub_app_rows: list[Adw.ActionRow] = []

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        page = Adw.PreferencesPage()

        package_group = Adw.PreferencesGroup(title=_("Package"))
        self._name_row = Adw.EntryRow(title=_("Package name"))
        package_group.add(self._name_row)

        self._environment_row, self._environments = _environment_combo(
            existing.environment if existing else None
        )
        package_group.add(self._environment_row)

        icon_row = Adw.ActionRow(
            title=_("Package icon"),
            subtitle=_("Without a chosen image, the first app's icon is used."),
        )
        self._icon_preview = Gtk.Image.new_from_icon_name("image-missing-symbolic")
        self._icon_preview.set_pixel_size(32)
        icon_row.add_prefix(self._icon_preview)
        choose_button = Gtk.Button(icon_name="document-open-symbolic", valign=Gtk.Align.CENTER,
                                   tooltip_text=_("Choose an image file"))
        choose_button.add_css_class("flat")
        choose_button.connect("clicked", self._on_choose_icon)
        icon_row.add_suffix(choose_button)
        gallery_button = Gtk.Button(icon_name="view-grid-symbolic", valign=Gtk.Align.CENTER,
                                    tooltip_text=_("Choose from the icon gallery"))
        gallery_button.add_css_class("flat")
        gallery_button.connect("clicked", self._on_open_gallery)
        icon_row.add_suffix(gallery_button)
        package_group.add(icon_row)
        page.add(package_group)

        self._apps_group = Adw.PreferencesGroup(title=_("Apps in the package"))
        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        store_button = Gtk.Button(valign=Gtk.Align.CENTER)
        store_button.set_child(Adw.ButtonContent(icon_name="org.gnome.Software-symbolic", label=_("Add from the Store")))
        store_button.add_css_class("flat")
        store_button.connect("clicked", self._on_add_from_store)
        add_box.append(store_button)
        custom_button = Gtk.Button(valign=Gtk.Align.CENTER)
        custom_button.set_child(Adw.ButtonContent(icon_name="list-add-symbolic", label=_("Add site")))
        custom_button.add_css_class("flat")
        custom_button.connect("clicked", self._on_add_custom)
        add_box.append(custom_button)
        self._apps_group.set_header_suffix(add_box)
        page.add(self._apps_group)

        actions_group = Adw.PreferencesGroup()
        self._save_button = Gtk.Button(label=_("Save changes") if existing else _("Create package"))
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

    def _load_existing(self, package: entries.PackageInfo) -> None:
        self._name_row.set_text(package.name)
        if package.icon_path and Path(package.icon_path).exists():
            self._icon_preview.set_from_file(package.icon_path)

        config_path = entries.PACKAGES_DIR / package.slug / "config.json"
        try:
            config = json.loads(config_path.read_text())
        except (OSError, json.JSONDecodeError):
            config = {"apps": []}
        for sub_app in config.get("apps", []):
            url = sub_app.get("url") or _url_from_exec(sub_app.get("exec", ""))
            if not url:
                continue
            icon = sub_app.get("icon")
            self._add_sub_app(sub_app.get("name", ""), url, icon if icon and Path(icon).exists() else None)

    def _add_sub_app(self, name: str, url: str, icon_source: str | None) -> None:
        entry = {"name": name, "url": url, "icon_source": icon_source}
        self._sub_apps.append(entry)

        row = Adw.ActionRow(title=name, subtitle=url)
        if icon_source:
            image = Gtk.Image.new_from_file(icon_source)
            image.set_pixel_size(28)
            row.add_prefix(image)
        else:
            row.add_prefix(Adw.Avatar(text=name, show_initials=True, size=28))
        remove_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
        remove_button.add_css_class("flat")
        remove_button.connect("clicked", self._on_remove_sub_app, entry, row)
        row.add_suffix(remove_button)

        self._apps_group.add(row)
        self._sub_app_rows.append(row)

    def _on_remove_sub_app(self, _button: Gtk.Button, entry: dict, row: Adw.ActionRow) -> None:
        self._sub_apps.remove(entry)
        self._sub_app_rows.remove(row)
        self._apps_group.remove(row)

    def _on_add_from_store(self, _button: Gtk.Button) -> None:
        dialog = StoreItemPickerDialog(on_pick=self._on_store_item_picked)
        dialog.present(self)

    def _on_store_item_picked(self, item: store.StoreItem) -> None:
        icon_path = store.save_icon_to_temp(item)
        self._add_sub_app(item.name, item.url, str(icon_path) if icon_path else None)

    def _on_add_custom(self, _button: Gtk.Button) -> None:
        dialog = CustomSiteDialog(on_confirm=lambda name, url: self._add_sub_app(name, url, None))
        dialog.present(self)

    def _on_choose_icon(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog(title=_("Choose the icon"))
        filters = Gio.ListStore.new(Gtk.FileFilter)
        image_filter = Gtk.FileFilter()
        image_filter.set_name(_("Images"))
        image_filter.add_mime_type("image/*")
        filters.append(image_filter)
        dialog.set_filters(filters)
        dialog.open(self.get_ancestor(Gtk.Window), None, self._on_icon_chosen)

    def _on_icon_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        if file and file.get_path():
            self._picked_icon_path = Path(file.get_path())
            self._icon_preview.set_from_file(file.get_path())

    def _on_open_gallery(self, _button: Gtk.Button) -> None:
        dialog = IconGalleryDialog(on_pick=self._on_gallery_icon_picked)
        dialog.present(self)

    def _on_gallery_icon_picked(self, path: Path) -> None:
        self._picked_icon_path = path
        self._icon_preview.set_from_file(str(path))

    def _toast(self, message: str) -> None:
        toast = Adw.Toast(title=message, timeout=3)
        root = self.get_ancestor(Gtk.Window)
        if isinstance(root, CascaWindow):
            root.toast_overlay.add_toast(toast)

    def _resolve_package_icon(self) -> Path | None:
        if self._picked_icon_path:
            return self._picked_icon_path
        for sub_app in self._sub_apps:
            icon = sub_app.get("icon_source")
            if icon and Path(icon).exists():
                return Path(icon)
        first_url = self._sub_apps[0]["url"]
        data = icons.fetch_favicon(first_url)
        if data:
            return icons.save_preview(data, "casca-package-icon")
        return None

    def _on_save(self, _button: Gtk.Button) -> None:
        name = self._name_row.get_text().strip()
        if not name:
            self._toast(_("Fill in the package name."))
            return
        if not self._sub_apps:
            self._toast(_("Add at least one app to the package."))
            return

        environment = _combo_environment_slug(self._environment_row, self._environments)
        try:
            if self._existing:
                entries.update_package(
                    self._existing.slug, name, self._sub_apps, self._picked_icon_path, environment
                )
            else:
                icon_path = self._resolve_package_icon()
                if icon_path is None:
                    self._toast(_("Could not set an icon. Choose an image manually."))
                    return
                entries.create_package(name, self._sub_apps, icon_path, environment)
        except (ValueError, KeyError, OSError) as error:
            self._toast(_("Error saving: %(error)s") % {"error": error})
            return

        self._on_saved()
        self._nav_view.pop()


def _url_from_exec(exec_cmd: str) -> str | None:
    """Recovers the site URL from an old package config.json (before packages
    stored "url" per sub-app) — the webkit Exec always carries --url=…"""
    match = re.search(r"--url=(\S+)", exec_cmd)
    return match.group(1).strip("'\"") if match else None


class EnvironmentEditorPage(Adw.NavigationPage):
    """Creates or edits an environment: name, banner/icon, info, notes and the
    defaults that prefill the editor for apps created inside it."""

    def __init__(self, nav_view: Adw.NavigationView, on_saved, existing: entries.EnvironmentInfo | None = None):
        super().__init__(title=_("Edit environment") if existing else _("New environment"))
        self._nav_view = nav_view
        self._on_saved = on_saved
        self._existing = existing
        self._detected_browsers = browsers.detect_browsers()
        self._banner_source: Path | None = None
        self._icon_source: Path | None = None

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        page = Adw.PreferencesPage()

        info_group = Adw.PreferencesGroup(title=_("Environment"))
        self._name_row = Adw.EntryRow(title=_("Environment name"))
        info_group.add(self._name_row)
        self._description_row = Adw.EntryRow(title=_("Description"))
        info_group.add(self._description_row)

        notes_row = Adw.ActionRow(title=_("Notes"))
        notes_row.set_activatable(False)
        info_group.add(notes_row)
        self._notes_view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self._notes_view.set_size_request(-1, 90)
        notes_frame = Gtk.Frame()
        notes_frame.set_child(self._notes_view)
        notes_frame.set_margin_start(12)
        notes_frame.set_margin_end(12)
        notes_frame.set_margin_bottom(12)
        notes_holder = Gtk.ListBoxRow(activatable=False, selectable=False, child=notes_frame)
        info_group.add(notes_holder)
        page.add(info_group)

        appearance_group = Adw.PreferencesGroup(title=_("Appearance"))
        banner_row = Adw.ActionRow(
            title=_("Banner"),
            subtitle=_("Wide image shown at the top of the environment window."),
        )
        self._banner_preview = Gtk.Image.new_from_icon_name("image-missing-symbolic")
        self._banner_preview.set_pixel_size(32)
        banner_row.add_prefix(self._banner_preview)
        banner_button = Gtk.Button(icon_name="document-open-symbolic", valign=Gtk.Align.CENTER,
                                   tooltip_text=_("Choose an image file"))
        banner_button.add_css_class("flat")
        banner_button.connect("clicked", self._on_choose_banner)
        banner_row.add_suffix(banner_button)
        appearance_group.add(banner_row)

        icon_row = Adw.ActionRow(
            title=_("Launcher icon"),
            subtitle=_("Shown in the applications menu; without one, the banner or Casca's icon is used."),
        )
        self._icon_preview = Gtk.Image.new_from_icon_name("image-missing-symbolic")
        self._icon_preview.set_pixel_size(32)
        icon_row.add_prefix(self._icon_preview)
        icon_file_button = Gtk.Button(icon_name="document-open-symbolic", valign=Gtk.Align.CENTER,
                                      tooltip_text=_("Choose an image file"))
        icon_file_button.add_css_class("flat")
        icon_file_button.connect("clicked", self._on_choose_icon)
        icon_row.add_suffix(icon_file_button)
        icon_gallery_button = Gtk.Button(icon_name="view-grid-symbolic", valign=Gtk.Align.CENTER,
                                         tooltip_text=_("Choose from the icon gallery"))
        icon_gallery_button.add_css_class("flat")
        icon_gallery_button.connect("clicked", self._on_open_gallery)
        icon_row.add_suffix(icon_gallery_button)
        appearance_group.add(icon_row)
        page.add(appearance_group)

        defaults_group = Adw.PreferencesGroup(
            title=_("Defaults for new apps"),
            description=_("Prefills the editor when you create an app in this environment."),
        )
        self._d_browser_row = Adw.ComboRow(title=_("Open with"))
        browser_labels = Gtk.StringList()
        for browser in self._detected_browsers:
            browser_labels.append(browser.label)
        self._d_browser_row.set_model(browser_labels)
        self._d_browser_row.connect("notify::selected", self._on_default_browser_changed)
        defaults_group.add(self._d_browser_row)

        self._d_profile_row = Adw.ComboRow(title=_("Browser account"))
        self._d_profile_options: list[str | None] = [None]
        defaults_group.add(self._d_profile_row)

        self._d_mobile_expander = Adw.ExpanderRow(title=_("Open in mobile mode"))
        self._d_mobile_expander.set_show_enable_switch(True)
        self._d_mobile_expander.set_enable_expansion(False)
        self._d_device_row = Adw.ComboRow(title=_("Device"))
        device_labels = Gtk.StringList()
        for device in devices.DEVICES:
            device_labels.append(device.label)
        self._d_device_row.set_model(device_labels)
        self._d_mobile_expander.add_row(self._d_device_row)
        defaults_group.add(self._d_mobile_expander)

        self._d_resolution_expander = Adw.ExpanderRow(title=_("Set window size"))
        self._d_resolution_expander.set_show_enable_switch(True)
        self._d_resolution_expander.set_enable_expansion(False)
        self._d_width_row = Adw.SpinRow(
            title=_("Width"), adjustment=Gtk.Adjustment(lower=200, upper=10000, step_increment=10, value=1280)
        )
        self._d_height_row = Adw.SpinRow(
            title=_("Height"), adjustment=Gtk.Adjustment(lower=200, upper=10000, step_increment=10, value=800)
        )
        self._d_resolution_expander.add_row(self._d_width_row)
        self._d_resolution_expander.add_row(self._d_height_row)
        defaults_group.add(self._d_resolution_expander)
        page.add(defaults_group)

        actions_group = Adw.PreferencesGroup()
        self._save_button = Gtk.Button(label=_("Save changes") if existing else _("Create environment"))
        self._save_button.add_css_class("suggested-action")
        self._save_button.add_css_class("pill")
        self._save_button.set_halign(Gtk.Align.CENTER)
        self._save_button.set_margin_top(12)
        self._save_button.connect("clicked", self._on_save)
        actions_group.add(self._save_button)
        page.add(actions_group)

        toolbar.set_content(page)
        self.set_child(toolbar)

        self._update_default_profile_options()
        if existing:
            self._load_existing(existing)

    def _load_existing(self, env: entries.EnvironmentInfo) -> None:
        self._name_row.set_text(env.name)
        self._description_row.set_text(env.description)
        self._notes_view.get_buffer().set_text(env.notes)
        if env.banner_path and Path(env.banner_path).exists():
            self._banner_preview.set_from_file(env.banner_path)
        if env.icon_path and Path(env.icon_path).exists():
            self._icon_preview.set_from_file(env.icon_path)

        defaults = env.defaults or {}
        browser_key = defaults.get("browser_key")
        if browser_key:
            for index, browser in enumerate(self._detected_browsers):
                if browser.key == browser_key:
                    self._d_browser_row.set_selected(index)
                    break
        self._update_default_profile_options()
        browser_profile = defaults.get("browser_profile")
        if browser_profile and browser_profile in self._d_profile_options:
            self._d_profile_row.set_selected(self._d_profile_options.index(browser_profile))
        self._d_mobile_expander.set_enable_expansion(bool(defaults.get("mobile")))
        device_key = defaults.get("device_key")
        if device_key:
            for index, device in enumerate(devices.DEVICES):
                if device.key == device_key:
                    self._d_device_row.set_selected(index)
                    break
        if defaults.get("width") and defaults.get("height"):
            self._d_resolution_expander.set_enable_expansion(True)
            self._d_width_row.set_value(defaults["width"])
            self._d_height_row.set_value(defaults["height"])

    def _on_default_browser_changed(self, *_args) -> None:
        self._update_default_profile_options()

    def _update_default_profile_options(self) -> None:
        selected = self._d_browser_row.get_selected()
        browser = (
            self._detected_browsers[selected]
            if self._detected_browsers and selected != Gtk.INVALID_LIST_POSITION
            else None
        )
        found = profiles.list_profiles(browser) if browser and browser.supports_account_profile else []
        labels = Gtk.StringList()
        labels.append(_("Isolated profile (new, no login)"))
        self._d_profile_options = [None]
        for profile in found:
            labels.append(profile.label)
            self._d_profile_options.append(profile.directory)
        self._d_profile_row.set_model(labels)
        self._d_profile_row.set_selected(0)
        self._d_profile_row.set_sensitive(browser is not None and browser.supports_account_profile)

    def _on_choose_banner(self, _button: Gtk.Button) -> None:
        self._open_image_dialog(self._on_banner_chosen)

    def _on_choose_icon(self, _button: Gtk.Button) -> None:
        self._open_image_dialog(self._on_icon_chosen)

    def _open_image_dialog(self, callback) -> None:
        dialog = Gtk.FileDialog(title=_("Choose an image file"))
        filters = Gio.ListStore.new(Gtk.FileFilter)
        image_filter = Gtk.FileFilter()
        image_filter.set_name(_("Images"))
        image_filter.add_mime_type("image/*")
        filters.append(image_filter)
        dialog.set_filters(filters)
        dialog.open(self.get_ancestor(Gtk.Window), None, callback)

    def _on_banner_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        if file and file.get_path():
            self._banner_source = Path(file.get_path())
            self._banner_preview.set_from_file(file.get_path())

    def _on_icon_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        if file and file.get_path():
            self._icon_source = Path(file.get_path())
            self._icon_preview.set_from_file(file.get_path())

    def _on_open_gallery(self, _button: Gtk.Button) -> None:
        dialog = IconGalleryDialog(on_pick=self._on_gallery_icon_picked)
        dialog.present(self)

    def _on_gallery_icon_picked(self, path: Path) -> None:
        self._icon_source = path
        self._icon_preview.set_from_file(str(path))

    def _toast(self, message: str) -> None:
        toast = Adw.Toast(title=message, timeout=3)
        root = self.get_ancestor(Gtk.Window)
        if isinstance(root, CascaWindow):
            root.toast_overlay.add_toast(toast)

    def _collect_defaults(self) -> dict:
        defaults: dict = {}
        selected = self._d_browser_row.get_selected()
        if self._detected_browsers and selected != Gtk.INVALID_LIST_POSITION:
            defaults["browser_key"] = self._detected_browsers[selected].key
        profile_selected = self._d_profile_row.get_selected()
        if profile_selected not in (0, Gtk.INVALID_LIST_POSITION) and profile_selected < len(self._d_profile_options):
            defaults["browser_profile"] = self._d_profile_options[profile_selected]
        if self._d_mobile_expander.get_enable_expansion():
            defaults["mobile"] = True
            defaults["device_key"] = devices.DEVICES[self._d_device_row.get_selected()].key
        if self._d_resolution_expander.get_enable_expansion():
            defaults["width"] = int(self._d_width_row.get_value())
            defaults["height"] = int(self._d_height_row.get_value())
        return defaults

    def _on_save(self, _button: Gtk.Button) -> None:
        name = self._name_row.get_text().strip()
        if not name:
            self._toast(_("Fill in the environment name."))
            return

        buffer = self._notes_view.get_buffer()
        notes = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False).strip()

        try:
            if self._existing:
                entries.update_environment(
                    self._existing.slug,
                    name,
                    description=self._description_row.get_text().strip(),
                    notes=notes,
                    banner_source=self._banner_source,
                    icon_source=self._icon_source,
                    defaults=self._collect_defaults(),
                )
            else:
                entries.create_environment(
                    name,
                    description=self._description_row.get_text().strip(),
                    notes=notes,
                    banner_source=self._banner_source,
                    icon_source=self._icon_source,
                    defaults=self._collect_defaults(),
                )
        except (ValueError, KeyError, OSError) as error:
            self._toast(_("Error saving: %(error)s") % {"error": error})
            return

        self._on_saved()
        self._nav_view.pop()


class PresetsPage(Adw.NavigationPage):
    """Screen with the list of preset sites, grouped by category."""

    def __init__(self, nav_view: Adw.NavigationView, on_refresh_list):
        super().__init__(title=_("Preset site"))
        self._nav_view = nav_view
        self._on_refresh_list = on_refresh_list

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        self._search_entry = Gtk.SearchEntry(placeholder_text=_("Search by name or category…"))
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
            subtitle = ngettext("%(n)d site", "%(n)d sites", len(category.presets)) % {"n": len(category.presets)}
            expander = Adw.ExpanderRow(title=category.title, subtitle=subtitle)
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
    "Artificial Intelligence": "chatgpt",
    "Social Media": "instagram",
}

_COUNTRY_FLAGS = {
    "Brazil": "🇧🇷",
    "United States": "🇺🇸",
    "Germany": "🇩🇪",
    "Poland": "🇵🇱",
    "Netherlands": "🇳🇱",
    "France": "🇫🇷",
    "United Kingdom": "🇬🇧",
    "Europe": "🇪🇺",
    "Argentina": "🇦🇷",
    "Uruguay": "🇺🇾",
    "Paraguay": "🇵🇾",
    "Colombia": "🇨🇴",
    "Chile": "🇨🇱",
    "Mexico": "🇲🇽",
    "Spain": "🇪🇸",
    "International": "🌐",
    "Global": "🌐",
}

_KIND_ICON_NAMES = {
    "Messenger": "system-users-symbolic",
    "Social Network": "face-smile-big-symbolic",
    "Video Streaming": "multimedia-player-symbolic",
    "Music Streaming": "audio-headphones-symbolic",
    "Artificial Intelligence": "starred-symbolic",
    "Search Engine": "system-search-symbolic",
    "Productivity": "view-list-symbolic",
    "PDF": "text-x-generic-symbolic",
    "Finance": "org.gnome.Calculator-symbolic",
    "Utility": "preferences-system-symbolic",
    "Conversion & Sharing": "send-to-symbolic",
    "Security": "channel-secure-symbolic",
    "Creativity": "insert-image-symbolic",
    "Cloud Computing": "network-server-symbolic",
}

# Facets that, in the Store, are their own "mode" (not a facet of the regular
# catalog) and always show grouped by country.
_COUNTRY_GROUPED_KINDS = {
    "marketplace": "Marketplace",
    "news": "News",
}


def _group_icon_widget(facet: str, key: str) -> Gtk.Widget:
    """Small leading icon for a group (company/package/country/kind bucket)."""
    if facet == "company":
        icon_path = social_icons.get_icon_path(_COMPANY_ICON_KEYS.get(key))
        if icon_path:
            image = Gtk.Image.new_from_file(str(icon_path))
            image.set_pixel_size(28)
            return image
        return Adw.Avatar(text=key, show_initials=True, size=28)

    if facet == "package":
        icon_path = social_icons.get_icon_path(_PACKAGE_ICON_KEYS.get(key))
        if icon_path:
            image = Gtk.Image.new_from_file(str(icon_path))
            image.set_pixel_size(28)
            return image
        return Gtk.Image.new_from_icon_name("view-grid-symbolic")

    if facet == "country":
        flag = _COUNTRY_FLAGS.get(key, "🌐")
        label = Gtk.Label()
        label.set_markup(f'<span font_desc="24">{GLib.markup_escape_text(flag)}</span>')
        return label

    icon_name = _KIND_ICON_NAMES.get(key, "view-grid-symbolic")
    image = Gtk.Image.new_from_icon_name(icon_name)
    image.set_pixel_size(24)
    return image


def _new_app_flowbox(compact: bool = False) -> Gtk.FlowBox:
    """Grid of horizontal app cards (icon left, name/description right), like
    GNOME Software's app tiles. Margin-less — the page hosting it sets margins."""
    flow = Gtk.FlowBox()
    if compact:
        flow.set_margin_top(6)
        flow.set_margin_bottom(6)
        flow.set_margin_start(6)
        flow.set_margin_end(6)
    flow.set_selection_mode(Gtk.SelectionMode.NONE)
    flow.set_homogeneous(True)
    flow.set_row_spacing(12)
    flow.set_column_spacing(12)
    flow.set_min_children_per_line(2)
    flow.set_max_children_per_line(3)
    return flow


def _new_category_flowbox() -> Gtk.FlowBox:
    """3-per-row grid for the Store home's category pills, like GNOME Software's."""
    flow = Gtk.FlowBox()
    flow.set_selection_mode(Gtk.SelectionMode.NONE)
    flow.set_homogeneous(True)
    flow.set_row_spacing(12)
    flow.set_column_spacing(12)
    flow.set_min_children_per_line(3)
    flow.set_max_children_per_line(3)
    return flow


def _section_label(text: str) -> Gtk.Label:
    """Bold left-aligned section header, like GNOME Software's "Editor's Choice"."""
    label = Gtk.Label(label=text, xalign=0)
    label.add_css_class("title-4")
    return label


# Gradient pairs cycled across category tiles — GNOME Software colors each category
# button distinctly instead of using flat/neutral cards, so we mirror that instead
# of the plain "card" style class used elsewhere in Casca.
_TILE_GRADIENTS: tuple[tuple[str, str], ...] = (
    ("#7c6cf6", "#a86ef0"),
    ("#e4c341", "#cf9a2e"),
    ("#f857a6", "#a75cf5"),
    ("#ef6c6c", "#f0a15c"),
    ("#33b679", "#1f8f5a"),
    ("#4a4a52", "#2e2e33"),
    ("#4aa3e0", "#2e6fcf"),
    ("#e05fae", "#b13ea0"),
    ("#58c4c0", "#2f9490"),
    ("#d97b3f", "#b85a2a"),
)

_store_css_loaded = False


def _ensure_store_css() -> None:
    """Loads the Store's gradient tile classes once per process."""
    global _store_css_loaded
    if _store_css_loaded:
        return
    _store_css_loaded = True

    rules = [
        ".casca-category-tile { border-radius: 12px; padding: 16px; }",
        ".casca-category-tile label { color: #ffffff; }",
        # Circular colored badges used by the detail page's context tiles, in the
        # style of GNOME Software's size/safety/adaptive/age row. alpha() keeps the
        # background readable in both light and dark themes.
        ".casca-circle { border-radius: 9999px; padding: 10px; }",
        ".casca-circle-grey { background: alpha(#77767b, 0.25); }",
        ".casca-circle-green { background: alpha(#33d17a, 0.22); color: #2ec27e; }",
        ".casca-circle-orange { background: alpha(#ff7800, 0.22); color: #e66100; }",
        ".casca-circle-gold { background: alpha(#f5c211, 0.28); }",
        ".casca-circle-silver { background: alpha(#c0bfbc, 0.30); }",
        ".casca-circle-bronze { background: alpha(#b5835a, 0.32); }",
    ]
    for index, (start, end) in enumerate(_TILE_GRADIENTS):
        rules.append(f".casca-cat-{index} {{ background: linear-gradient(135deg, {start}, {end}); }}")

    provider = Gtk.CssProvider()
    provider.load_from_data("\n".join(rules).encode())
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def _build_category_tile(icon_widget: Gtk.Widget, title: str, tooltip: str, gradient_index: int, on_click) -> Gtk.Widget:
    """Colorful gradient pill — icon and label centered side by side, exactly like
    GNOME Software's category buttons on the Explore page."""
    _ensure_store_css()
    button = Gtk.Button(tooltip_text=tooltip)
    button.add_css_class("flat")
    button.add_css_class("casca-category-tile")
    button.add_css_class(f"casca-cat-{gradient_index % len(_TILE_GRADIENTS)}")
    button.set_hexpand(True)
    button.set_size_request(-1, 60)
    button.connect("clicked", lambda _btn: on_click())

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
    box.append(icon_widget)
    title_label = Gtk.Label(label=title)
    title_label.set_ellipsize(Pango.EllipsizeMode.END)
    title_label.add_css_class("heading")
    box.append(title_label)

    button.set_child(box)
    return button


def _build_app_tile(item: store.StoreItem, on_click) -> Gtk.Widget:
    """Horizontal app card — icon on the left, name and short description on the
    right — like GNOME Software's "Editor's Choice" tiles."""
    icon_path = store.save_icon_to_temp(item)
    if icon_path:
        image = Gtk.Image.new_from_file(str(icon_path))
        image.set_pixel_size(48)
    else:
        image = Adw.Avatar(text=item.name, show_initials=True, size=48)
    image.set_valign(Gtk.Align.CENTER)

    button = Gtk.Button(tooltip_text=f"{item.name} — {item.company}")
    button.add_css_class("flat")
    button.add_css_class("card")
    button.set_hexpand(True)
    button.set_size_request(-1, 88)
    button.connect("clicked", lambda _btn: on_click())

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, valign=Gtk.Align.CENTER)
    box.set_margin_top(12)
    box.set_margin_bottom(12)
    box.set_margin_start(12)
    box.set_margin_end(12)
    box.append(image)

    text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, valign=Gtk.Align.CENTER, hexpand=True)
    name_label = Gtk.Label(label=item.name, xalign=0)
    name_label.set_ellipsize(Pango.EllipsizeMode.END)
    name_label.add_css_class("heading")
    text_box.append(name_label)

    description_label = Gtk.Label(label=store.kind_info(item.kind).blurb, xalign=0, wrap=True)
    description_label.set_lines(2)
    description_label.set_ellipsize(Pango.EllipsizeMode.END)
    description_label.add_css_class("caption")
    description_label.add_css_class("dim-label")
    text_box.append(description_label)

    box.append(text_box)
    button.set_child(box)
    return button


def _pick_featured(items: list[store.StoreItem], count: int = 6) -> list[store.StoreItem]:
    """A handful of Gold-tier, well-known apps for the Store home's featured
    carousel — at most one per category AND one per company, for variety."""
    featured: list[store.StoreItem] = []
    seen_kinds: set[str] = set()
    seen_companies: set[str] = set()
    for item in items:
        if item.company not in store.VERIFIED_COMPANIES:
            continue
        if item.kind in seen_kinds or item.company in seen_companies:
            continue
        if store.rank_badge(item).tier != _("Gold"):
            continue
        seen_kinds.add(item.kind)
        seen_companies.add(item.company)
        featured.append(item)
        if len(featured) >= count:
            break
    return featured


def _pick_editor_choice(items: list[store.StoreItem], exclude: list[store.StoreItem], count: int = 9) -> list[store.StoreItem]:
    """Gold-tier verified apps for the home's "Editor's Choice" grid — one per
    company, skipping anything already in the featured carousel."""
    exclude_names = {item.name for item in exclude}
    seen_companies = {item.company for item in exclude}
    picks: list[store.StoreItem] = []
    for item in items:
        if item.name in exclude_names or item.company in seen_companies:
            continue
        if item.company not in store.VERIFIED_COMPANIES:
            continue
        if store.rank_badge(item).tier != _("Gold"):
            continue
        seen_companies.add(item.company)
        picks.append(item)
        if len(picks) >= count:
            break
    return picks


class StoreWindow(Adw.ApplicationWindow):
    """Casca Store: its own window, browsed by category grid (Play Store/App Store
    style) instead of the old company/type/package facet tabs. Owns the catalog and
    acts as the shared controller for its internal navigation stack (home → category
    → app detail / company), so every page just holds a reference back to it."""

    def __init__(self, parent: Adw.ApplicationWindow, nav_view: Adw.NavigationView, on_refresh_list):
        super().__init__(
            application=parent.get_application(),
            transient_for=parent,
            default_width=640,
            default_height=800,
            title=_("Casca Store"),
        )
        self._app_nav_view = nav_view
        self._on_refresh_list = on_refresh_list

        self.all_items = store.fetch_catalog()
        special_kinds = set(_COUNTRY_GROUPED_KINDS.values())
        self.catalog_items = [item for item in self.all_items if item.kind not in special_kinds]
        self.kind_pools = {
            facet_key: [item for item in self.all_items if item.kind == kind]
            for facet_key, kind in _COUNTRY_GROUPED_KINDS.items()
        }

        self.regions = [store.GLOBAL_REGION] + store.available_regions(self.all_items)
        self.region = store.detect_default_region(self.regions)

        self._toast_overlay = Adw.ToastOverlay()
        self._store_nav = Adw.NavigationView()
        self._store_nav.push(StoreHomePage(self))
        self._toast_overlay.set_child(self._store_nav)
        self.set_content(self._toast_overlay)

    def toast(self, message: str) -> None:
        self._toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def push(self, page: Adw.NavigationPage) -> None:
        self._store_nav.push(page)

    def filtered_catalog_items(self) -> list[store.StoreItem]:
        return [item for item in self.catalog_items if store.region_matches(item, self.region)]

    def filtered_kind_pool(self, facet_key: str) -> list[store.StoreItem]:
        return [item for item in self.kind_pools.get(facet_key, []) if store.region_matches(item, self.region)]

    def open_editor_for(self, item: store.StoreItem) -> None:
        editor = EditorPage(self._app_nav_view, on_saved=self._on_refresh_list)
        self._app_nav_view.push(editor)
        editor._on_store_item_picked(item)
        self.close()

    def install_package(self, package_name: str, items: list[store.StoreItem]) -> None:
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
            self.toast(_("Could not set an icon for %(name)s.") % {"name": package_name})
            return

        try:
            entries.create_package(package_name, sub_apps, package_icon)
        except ValueError as error:
            self.toast(_("Error installing package: %(error)s") % {"error": error})
            return

        self._on_refresh_list()
        self.toast(
            ngettext(
                "Package “%(name)s” installed with %(n)d app.",
                "Package “%(name)s” installed with %(n)d apps.",
                len(items),
            )
            % {"name": package_name, "n": len(items)}
        )


class StoreHomePage(Adw.NavigationPage):
    """Store home: a grid of categories to browse (icons separated by area), plus a
    global search across the whole catalog."""

    def __init__(self, store_window: StoreWindow):
        super().__init__(title=_("Casca Store"))
        self._store_window = store_window
        self._carousel_timeout_id: int | None = None

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        top_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        top_box.set_margin_start(12)
        top_box.set_margin_end(12)
        top_box.set_margin_top(12)

        search_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._search_entry = Gtk.SearchEntry(placeholder_text=_("Search apps and sites…"), hexpand=True)
        self._search_entry.connect("changed", self._on_search_changed)
        search_row.append(self._search_entry)
        search_row.append(self._build_region_dropdown())
        top_box.append(search_row)

        self._scrolled = Gtk.ScrolledWindow(vexpand=True)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.append(top_box)
        content_box.append(self._scrolled)
        toolbar.set_content(content_box)
        self.set_child(toolbar)
        self.connect("destroy", self._on_destroy)

        self._show_categories()

    def _build_region_dropdown(self) -> Gtk.DropDown:
        labels = Gtk.StringList()
        for region in self._store_window.regions:
            flag = _COUNTRY_FLAGS.get(region, "🌐")
            labels.append(f"{flag} {_(region)}")

        dropdown = Gtk.DropDown(model=labels, tooltip_text=_("Region"))
        try:
            dropdown.set_selected(self._store_window.regions.index(self._store_window.region))
        except ValueError:
            dropdown.set_selected(0)
        dropdown.connect("notify::selected", self._on_region_changed)
        return dropdown

    def _on_region_changed(self, dropdown: Gtk.DropDown, _pspec) -> None:
        index = dropdown.get_selected()
        if 0 <= index < len(self._store_window.regions):
            self._store_window.region = self._store_window.regions[index]
        if self._search_entry.get_text().strip():
            self._on_search_changed(self._search_entry)
        else:
            self._show_categories()

    def _cancel_carousel_autoplay(self) -> None:
        if self._carousel_timeout_id is not None:
            GLib.source_remove(self._carousel_timeout_id)
            self._carousel_timeout_id = None

    def _on_destroy(self, _widget) -> None:
        self._cancel_carousel_autoplay()

    def _show_categories(self) -> None:
        self._cancel_carousel_autoplay()
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        body.set_margin_start(12)
        body.set_margin_end(12)
        body.set_margin_top(6)
        body.set_margin_bottom(18)

        catalog_items = self._store_window.filtered_catalog_items()

        featured = _pick_featured(catalog_items)
        if featured:
            body.append(self._build_carousel(featured))

        flow = _new_category_flowbox()
        gradient_index = 0

        grouped_kind = store.group_by(catalog_items, "kind")
        for kind, icon_name in _KIND_ICON_NAMES.items():
            items = grouped_kind.get(kind, [])
            if not items:
                continue
            tooltip = ngettext("%(n)d site", "%(n)d sites", len(items)) % {"n": len(items)}
            image = Gtk.Image.new_from_icon_name(icon_name)
            image.set_pixel_size(20)
            flow.append(
                _build_category_tile(
                    image, _(kind), tooltip, gradient_index, lambda k=kind, i=items: self._open_category(_(k), i)
                )
            )
            gradient_index += 1

        packages = {
            key: items
            for key, items in store.group_by(catalog_items, "package").items()
            if key != _("Independent apps")
        }
        if packages:
            package_items = [item for items in packages.values() for item in items]
            tooltip = ngettext("%(n)d package", "%(n)d packages", len(packages)) % {"n": len(packages)}
            image = Gtk.Image.new_from_icon_name("view-grid-symbolic")
            image.set_pixel_size(20)
            flow.append(
                _build_category_tile(
                    image,
                    _("Packages"),
                    tooltip,
                    gradient_index,
                    lambda i=package_items: self._open_grouped(_("Packages"), i, "package"),
                )
            )
            gradient_index += 1

        for facet_key, kind_label in _COUNTRY_GROUPED_KINDS.items():
            items = self._store_window.filtered_kind_pool(facet_key)
            if not items:
                continue
            tooltip = ngettext("%(n)d site", "%(n)d sites", len(items)) % {"n": len(items)}
            label = Gtk.Label()
            label.set_markup('<span font_desc="16">🌐</span>')
            flow.append(
                _build_category_tile(
                    label,
                    _(kind_label),
                    tooltip,
                    gradient_index,
                    lambda i=items, l=kind_label: self._open_grouped(_(l), i, "country"),
                )
            )
            gradient_index += 1

        body.append(_section_label(_("Categories")))
        body.append(flow)

        editor_picks = _pick_editor_choice(catalog_items, exclude=featured)
        if editor_picks:
            body.append(_section_label(_("Editor's Choice")))
            picks_flow = _new_app_flowbox()
            for item in editor_picks:
                picks_flow.append(_build_app_tile(item, lambda i=item: self._open_detail(i)))
            body.append(picks_flow)

        self._scrolled.set_child(body)

    def _build_carousel(self, featured: list[store.StoreItem]) -> Gtk.Widget:
        carousel = Adw.Carousel()
        carousel.set_size_request(-1, 220)
        for item in featured:
            carousel.append(self._build_carousel_page(item))

        dots = Adw.CarouselIndicatorDots(carousel=carousel)
        dots.set_halign(Gtk.Align.CENTER)

        overlay = Gtk.Overlay()
        overlay.set_child(carousel)

        prev_button = Gtk.Button(icon_name="go-previous-symbolic", valign=Gtk.Align.CENTER, halign=Gtk.Align.START)
        prev_button.add_css_class("circular")
        prev_button.add_css_class("osd")
        prev_button.set_margin_start(8)
        prev_button.connect("clicked", lambda _b: self._scroll_carousel(carousel, -1))
        overlay.add_overlay(prev_button)

        next_button = Gtk.Button(icon_name="go-next-symbolic", valign=Gtk.Align.CENTER, halign=Gtk.Align.END)
        next_button.add_css_class("circular")
        next_button.add_css_class("osd")
        next_button.set_margin_end(8)
        next_button.connect("clicked", lambda _b: self._scroll_carousel(carousel, 1))
        overlay.add_overlay(next_button)

        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        wrapper.append(overlay)
        wrapper.append(dots)

        if carousel.get_n_pages() > 1:
            self._carousel_timeout_id = GLib.timeout_add_seconds(5, self._autoplay_tick, carousel)
        return wrapper

    def _autoplay_tick(self, carousel: Adw.Carousel) -> bool:
        if carousel.get_root() is None:
            self._carousel_timeout_id = None
            return GLib.SOURCE_REMOVE
        self._scroll_carousel(carousel, 1)
        return GLib.SOURCE_CONTINUE

    def _build_carousel_page(self, item: store.StoreItem) -> Gtk.Widget:
        icon_path = store.save_icon_to_temp(item)
        rgb = icons.dominant_color(icon_path) if icon_path else (90, 90, 90)
        text_color = icons.contrasting_text_color(rgb)
        css_class = f"casca-featured-{next(_header_class_counter)}"
        provider = Gtk.CssProvider()
        provider.load_from_data(
            (
                f".{css_class} {{ background: {icons.to_hex(rgb)}; border-radius: 16px; }}"
                f".{css_class} label {{ color: {text_color}; }}"
            ).encode()
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        button = Gtk.Button()
        button.add_css_class("flat")
        button.add_css_class(css_class)
        button.connect("clicked", lambda _b, i=item: self._open_detail(i))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        if icon_path:
            image = Gtk.Image.new_from_file(str(icon_path))
            image.set_pixel_size(64)
        else:
            image = Adw.Avatar(text=item.name, show_initials=True, size=64)
        box.append(image)

        name_label = Gtk.Label(label=item.name)
        name_label.add_css_class("title-1")
        box.append(name_label)

        blurb_label = Gtk.Label(
            label=store.kind_info(item.kind).blurb, wrap=True, justify=Gtk.Justification.CENTER
        )
        blurb_label.set_max_width_chars(44)
        blurb_label.add_css_class("caption")
        box.append(blurb_label)

        button.set_child(box)
        return button

    def _scroll_carousel(self, carousel: Adw.Carousel, delta: int) -> None:
        n_pages = carousel.get_n_pages()
        if n_pages == 0:
            return
        target = (round(carousel.get_position()) + delta) % n_pages
        carousel.scroll_to(carousel.get_nth_page(target), True)

    def _open_category(self, title: str, items: list[store.StoreItem]) -> None:
        self._store_window.push(CategoryPage(self._store_window, title, items))

    def _open_grouped(self, title: str, items: list[store.StoreItem], group_facet: str) -> None:
        self._store_window.push(CategoryPage(self._store_window, title, items, group_facet=group_facet))

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        query = _fold(entry.get_text().strip())
        if not query:
            self._show_categories()
            return

        self._cancel_carousel_autoplay()
        all_items = self._store_window.filtered_catalog_items() + [
            item
            for facet_key in _COUNTRY_GROUPED_KINDS
            for item in self._store_window.filtered_kind_pool(facet_key)
        ]
        matches = [item for item in all_items if query in _fold(item.name) or query in _fold(item.company)]
        if not matches:
            status = Adw.StatusPage(icon_name="system-search-symbolic", title=_("No results"))
            self._scrolled.set_child(status)
            return

        flow = _new_app_flowbox()
        flow.set_margin_top(6)
        flow.set_margin_bottom(12)
        flow.set_margin_start(12)
        flow.set_margin_end(12)
        for item in matches:
            flow.append(_build_app_tile(item, lambda i=item: self._open_detail(i)))
        self._scrolled.set_child(flow)

    def _open_detail(self, item: store.StoreItem) -> None:
        self._store_window.push(AppDetailPage(self._store_window, item))


class CategoryPage(Adw.NavigationPage):
    """One area of the Store: either a flat grid of app icons (a category, a
    company, or search results) or — for the "Packages"/"Marketplaces"/"News" home
    tiles — an accordion of sub-groups, each with its own grid inside."""

    def __init__(
        self,
        store_window: StoreWindow,
        title: str,
        items: list[store.StoreItem],
        group_facet: str | None = None,
    ):
        super().__init__(title=title)
        self._store_window = store_window
        self._items = items
        self._group_facet = group_facet
        self._flat_entries: list[tuple[store.StoreItem, Gtk.Widget]] = []
        self._grouped_entries: list[tuple[str, Adw.ExpanderRow, list[tuple[store.StoreItem, Gtk.Widget]]]] = []

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        top_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        top_box.set_margin_start(12)
        top_box.set_margin_end(12)
        top_box.set_margin_top(12)
        self._search_entry = Gtk.SearchEntry(placeholder_text=_("Search by name…"))
        self._search_entry.connect("changed", self._on_search_changed)
        top_box.append(self._search_entry)

        self._scrolled = Gtk.ScrolledWindow(vexpand=True)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.append(top_box)
        content_box.append(self._scrolled)
        toolbar.set_content(content_box)
        self.set_child(toolbar)

        if group_facet is None:
            self._build_flat()
        else:
            self._build_grouped()

    def _build_flat(self) -> None:
        flow = _new_app_flowbox()
        flow.set_margin_top(6)
        flow.set_margin_bottom(12)
        flow.set_margin_start(12)
        flow.set_margin_end(12)
        for item in self._items:
            tile = _build_app_tile(item, lambda i=item: self._open_detail(i))
            flow.append(tile)
            self._flat_entries.append((item, tile))
        self._scrolled.set_child(flow)

    def _build_grouped(self) -> None:
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()
        grouped = store.group_by(self._items, self._group_facet)
        for key, items in grouped.items():
            subtitle = ngettext("%(n)d site", "%(n)d sites", len(items)) % {"n": len(items)}
            expander = Adw.ExpanderRow(title=_(key), subtitle=subtitle)
            expander.add_prefix(_group_icon_widget(self._group_facet, key))
            if self._group_facet == "package" and key != _("Independent apps"):
                install_button = Gtk.Button(label=_("Install full package"), valign=Gtk.Align.CENTER)
                install_button.add_css_class("flat")
                install_button.connect("clicked", self._on_install_package, key, items)
                expander.add_suffix(install_button)

            flow = _new_app_flowbox(compact=True)
            entries_for_group: list[tuple[store.StoreItem, Gtk.Widget]] = []
            for item in items:
                tile = _build_app_tile(item, lambda i=item: self._open_detail(i))
                flow.append(tile)
                entries_for_group.append((item, tile))
            expander.add_row(flow)

            group.add(expander)
            self._grouped_entries.append((key, expander, entries_for_group))
        page.add(group)
        self._scrolled.set_child(page)

    def _on_install_package(self, _button: Gtk.Button, package_name: str, items: list[store.StoreItem]) -> None:
        self._store_window.install_package(package_name, items)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        query = _fold(entry.get_text().strip())

        if self._flat_entries:
            for item, tile in self._flat_entries:
                tile.set_visible(not query or query in _fold(item.name) or query in _fold(item.company))
            return

        for key, expander, entries_for_group in self._grouped_entries:
            group_matches = not query or query in _fold(key)
            any_visible = False
            for item, tile in entries_for_group:
                visible = group_matches or query in _fold(item.name)
                tile.set_visible(visible)
                any_visible = any_visible or visible
            expander.set_visible(any_visible)
            expander.set_expanded(any_visible and bool(query))

    def _open_detail(self, item: store.StoreItem) -> None:
        self._store_window.push(AppDetailPage(self._store_window, item))


class AppDetailPage(Adw.NavigationPage):
    """App detail: header bar colored from the app's own icon, plus everything the
    Store knows about the site — what it is, its usage tags, the Casca quality
    seal, disk-space savings, possible PC access and security properties."""

    _BADGE_EMOJI = {"Gold": "🥇", "Silver": "🥈", "Bronze": "🥉"}

    def __init__(self, store_window: StoreWindow, item: store.StoreItem):
        super().__init__(title=item.name)
        self._store_window = store_window
        self._item = item

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header_css_class = f"casca-header-{next(_header_class_counter)}"
        header.add_css_class(header_css_class)
        header_css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), header_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        icon_path = store.save_icon_to_temp(item)
        if icon_path:
            header_icon = Gtk.Image.new_from_file(str(icon_path))
            header_icon.set_pixel_size(20)
            header.pack_start(header_icon)
            rgb = icons.dominant_color(icon_path)
            css = build_header_css(header_css_class, icons.to_hex(rgb), icons.contrasting_text_color(rgb))
            header_css_provider.load_from_data(css.encode())
        toolbar.add_top_bar(header)

        page = Adw.PreferencesPage()
        page.add(self._build_header_section(item, icon_path))
        page.add(self._build_summary_group(item))

        info_group = Adw.PreferencesGroup()
        info_group.add(self._build_info_tiles_row(item))
        page.add(info_group)

        page.add(self._build_pc_access_group(item))
        page.add(self._build_security_group())
        page.add(self._build_about_group(item))

        more_group = self._build_more_from_company_group(item)
        if more_group is not None:
            page.add(more_group)

        toolbar.set_content(page)
        self.set_child(toolbar)

    def _badge_tier_key(self, badge: store.BadgeInfo) -> str:
        if badge.tier == _("Gold"):
            return "gold"
        if badge.tier == _("Silver"):
            return "silver"
        return "bronze"

    def _build_header_section(self, item: store.StoreItem, icon_path: Path | None) -> Adw.PreferencesGroup:
        """Icon + name + company/verified + seal + Add button, in a row like GNOME
        Software's app header band."""
        group = Adw.PreferencesGroup()
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18, valign=Gtk.Align.CENTER)
        row.set_margin_top(12)
        row.set_margin_bottom(4)

        if icon_path:
            image = Gtk.Image.new_from_file(str(icon_path))
            image.set_pixel_size(96)
        else:
            image = Adw.Avatar(text=item.name, show_initials=True, size=96)
        image.set_valign(Gtk.Align.CENTER)
        row.append(image)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True, valign=Gtk.Align.CENTER)
        name_label = Gtk.Label(label=item.name, xalign=0)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_label.add_css_class("title-1")
        text_box.append(name_label)

        company_label = Gtk.Label(label=item.company, xalign=0)
        company_label.add_css_class("dim-label")
        text_box.append(company_label)

        badges_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        if item.company in store.VERIFIED_COMPANIES:
            verified_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            verified_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
            verified_icon.set_pixel_size(14)
            verified_icon.add_css_class("accent")
            verified_box.append(verified_icon)
            verified_label = Gtk.Label(label=_("Verified"))
            verified_label.add_css_class("caption")
            verified_label.add_css_class("accent")
            verified_box.append(verified_label)
            badges_box.append(verified_box)
        badges_box.append(self._build_seal_chip(store.rank_badge(item)))
        text_box.append(badges_box)

        row.append(text_box)

        add_button = Gtk.Button(tooltip_text=_("Add to Casca"), valign=Gtk.Align.CENTER)
        add_button.set_child(Adw.ButtonContent(icon_name="list-add-symbolic", label=_("Add")))
        add_button.add_css_class("suggested-action")
        add_button.add_css_class("pill")
        add_button.connect("clicked", self._on_add_clicked)
        row.append(add_button)

        group.add(row)
        return group

    def _build_seal_chip(self, badge: store.BadgeInfo) -> Gtk.Widget:
        """Small inline seal indicator under the app name — GNOME shows the star
        rating there; Casca shows its Bronze/Silver/Gold seal, with the sub-score
        popover a click away."""
        button = Gtk.MenuButton()
        button.add_css_class("flat")
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        emoji_label = Gtk.Label(label=self._BADGE_EMOJI.get(badge.tier, "🥉"))
        content.append(emoji_label)
        text_label = Gtk.Label(label=_("Casca Seal: %(tier)s") % {"tier": badge.tier})
        text_label.add_css_class("caption")
        content.append(text_label)
        button.set_child(content)
        popover = Gtk.Popover()
        popover.set_child(self._build_badge_popover(badge))
        button.set_popover(popover)
        return button

    def _build_summary_group(self, item: store.StoreItem) -> Adw.PreferencesGroup:
        """Bold summary + description paragraph + tag chips, like the "what it
        does" block under GNOME Software's screenshots."""
        group = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        summary_label = Gtk.Label(label=store.kind_info(item.kind).blurb, xalign=0, wrap=True)
        summary_label.add_css_class("title-4")
        box.append(summary_label)

        domain = urlparse(item.url).netloc or item.url
        description_label = Gtk.Label(
            label=_(
                "%(name)s, by %(company)s, opens straight from %(domain)s in its own "
                "window — no installation and no downloads. Casca creates the menu "
                "shortcut and keeps the site's data in a profile that's separate from "
                "your browser."
            )
            % {"name": item.name, "company": item.company, "domain": domain},
            xalign=0,
            wrap=True,
        )
        description_label.add_css_class("dim-label")
        box.append(description_label)

        tags = store.usage_tags(item)
        if tags:
            box.append(self._build_tags_row(tags))

        group.add(box)
        return group

    def _build_context_tile(
        self, circle_css: str, icon_name: str | None, title: str, caption: str, emoji: str | None = None
    ) -> Gtk.Widget:
        """One column of the context row: colored circular badge on top, bold
        title, small caption — GNOME Software's size/safety/age-rating tile."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.CENTER, hexpand=True)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(8)
        box.set_margin_end(8)

        circle = Gtk.Box(halign=Gtk.Align.CENTER)
        circle.add_css_class("casca-circle")
        circle.add_css_class(circle_css)
        if emoji is not None:
            emoji_label = Gtk.Label()
            emoji_label.set_markup(f'<span font_desc="14">{emoji}</span>')
            circle.append(emoji_label)
        elif icon_name:
            image = Gtk.Image.new_from_icon_name(icon_name)
            image.set_pixel_size(16)
            circle.append(image)
        box.append(circle)

        title_label = Gtk.Label(label=title, wrap=True, justify=Gtk.Justification.CENTER)
        title_label.add_css_class("heading")
        box.append(title_label)

        caption_label = Gtk.Label(label=caption, wrap=True, justify=Gtk.Justification.CENTER)
        caption_label.set_max_width_chars(18)
        caption_label.add_css_class("caption")
        caption_label.add_css_class("dim-label")
        box.append(caption_label)
        return box

    def _build_info_tiles_row(self, item: store.StoreItem) -> Gtk.Widget:
        """One card with 4 columns split by hairlines — the glanceable context row
        from GNOME Software (size/safety/adaptive/age), with what Casca knows."""
        _ensure_store_css()
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        card.add_css_class("card")
        info = store.kind_info(item.kind)

        low, high = info.space_range_mb
        tiles: list[Gtk.Widget] = [
            self._build_context_tile(
                "casca-circle-grey", "drive-harddisk-symbolic", f"~{low}–{high} MB", _("Estimated disk savings")
            ),
            self._build_context_tile(
                "casca-circle-green", "channel-secure-symbolic", _("Isolated"), _("HTTPS and its own profile")
            ),
        ]

        if info.pc_access:
            access_labels = [store.PC_ACCESS_LABELS.get(key, (None, key))[1] for key in info.pc_access]
            caption = ", ".join(access_labels[:3]) + ("…" if len(access_labels) > 3 else "")
            tiles.append(
                self._build_context_tile(
                    "casca-circle-orange",
                    "dialog-warning-symbolic",
                    ngettext("%(n)d possible access", "%(n)d possible accesses", len(info.pc_access))
                    % {"n": len(info.pc_access)},
                    caption,
                )
            )
        else:
            tiles.append(
                self._build_context_tile(
                    "casca-circle-green", "emblem-ok-symbolic", _("No special access"), _("Doesn't typically ask for any")
                )
            )

        badge = store.rank_badge(item)
        seal_content = self._build_context_tile(
            f"casca-circle-{self._badge_tier_key(badge)}",
            None,
            _("%(tier)s Seal") % {"tier": badge.tier},
            _("Click for details"),
            emoji=self._BADGE_EMOJI.get(badge.tier, "🥉"),
        )
        seal_button = Gtk.MenuButton(hexpand=True)
        seal_button.add_css_class("flat")
        seal_button.set_child(seal_content)
        popover = Gtk.Popover()
        popover.set_child(self._build_badge_popover(badge))
        seal_button.set_popover(popover)
        tiles.append(seal_button)

        for index, tile in enumerate(tiles):
            if index:
                card.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
            card.append(tile)
        return card

    def _build_badge_popover(self, badge: store.BadgeInfo) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(12)
        box.set_margin_end(12)

        title = Gtk.Label(label=_("Casca-estimated quality seal"), wrap=True)
        title.add_css_class("heading")
        box.append(title)

        for key, label in (
            ("updates", _("Updates")),
            ("usability", _("Usability")),
            ("speed", _("Speed")),
            ("community", _("Community")),
        ):
            score = badge.scores[key]
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.append(Gtk.Label(label=label, xalign=0, hexpand=True))
            row.append(Gtk.Label(label="●" * score + "○" * (3 - score)))
            box.append(row)

        disclaimer = Gtk.Label(
            label=_(
                "Estimate calculated by Casca from the company's recognition and the "
                "app's category — not an official rating from the site."
            ),
            wrap=True,
        )
        disclaimer.set_max_width_chars(28)
        disclaimer.add_css_class("caption")
        disclaimer.add_css_class("dim-label")
        box.append(disclaimer)
        return box

    def _build_tags_row(self, tags: tuple[str, ...]) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.START)
        box.set_margin_top(4)
        for tag in tags:
            label = Gtk.Label(label=tag)
            label.add_css_class("caption")
            label.add_css_class("card")
            label.set_margin_start(2)
            label.set_margin_end(2)
            box.append(label)
        return box

    def _build_about_group(self, item: store.StoreItem) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=_("Company"))
        company_row = Adw.ActionRow(
            title=item.company,
            subtitle=_("See all apps from this company"),
            activatable=True,
        )
        company_row.add_prefix(_group_icon_widget("company", item.company))
        company_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        company_row.connect("activated", self._on_company_activated)
        group.add(company_row)
        return group

    def _build_pc_access_group(self, item: store.StoreItem) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title=_("Possible access to your computer"),
            description=_("Typical pattern for this category — not a scan of this specific site."),
        )
        access = store.kind_info(item.kind).pc_access
        if access:
            for key in access:
                icon_name, label = store.PC_ACCESS_LABELS.get(key, ("dialog-question-symbolic", key))
                row = Adw.ActionRow(title=label)
                row.add_prefix(Gtk.Image.new_from_icon_name(icon_name))
                group.add(row)
        else:
            row = Adw.ActionRow(title=_("Doesn't typically request special access"))
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            group.add(row)
        return group

    def _build_security_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=_("Security"))
        for icon_name, title, subtitle in (
            (
                "channel-secure-symbolic",
                _("HTTPS connection"),
                _("Casca only opens sites over an encrypted connection."),
            ),
            (
                "system-users-symbolic",
                _("Isolated browser profile"),
                _(
                    "Each app you create gets its own profile, separate from your main "
                    "browser and from your other apps."
                ),
            ),
            (
                "package-x-generic-symbolic",
                _("No native executable installed"),
                _("Only a shortcut is created — nothing runs outside the browser engine."),
            ),
        ):
            row = Adw.ActionRow(title=title, subtitle=subtitle)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon_name))
            group.add(row)
        return group

    def _build_more_from_company_group(self, item: store.StoreItem) -> Adw.PreferencesGroup | None:
        others = [
            other
            for other in store.group_by(self._store_window.all_items, "company").get(item.company, [])
            if other.name != item.name
        ]
        if not others:
            return None

        group = Adw.PreferencesGroup(title=_("More from %(company)s") % {"company": item.company})
        flow = _new_app_flowbox(compact=True)
        for other in others[:6]:
            flow.append(_build_app_tile(other, lambda i=other: self._open_other(i)))
        group.add(flow)
        return group

    def _on_company_activated(self, _row: Adw.ActionRow) -> None:
        items = store.group_by(self._store_window.all_items, "company").get(self._item.company, [])
        self._store_window.push(CategoryPage(self._store_window, self._item.company, items))

    def _on_add_clicked(self, _button: Gtk.Button) -> None:
        self._store_window.open_editor_for(self._item)

    def _open_other(self, item: store.StoreItem) -> None:
        self._store_window.push(AppDetailPage(self._store_window, item))


class HelpWindow(Adw.ApplicationWindow):
    """Casca's user guide, rendered from help_content.py in the app's active language."""

    def __init__(self, parent: Adw.ApplicationWindow, anchor: str | None = None):
        super().__init__(
            application=parent.get_application(),
            transient_for=parent,
            default_width=780,
            default_height=760,
            title=_("Casca Manual"),
        )
        self._anchor = anchor

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        data_dir = Path(__file__).parent / "data"
        try:
            gi.require_version("WebKit", "6.0")
            from gi.repository import WebKit

            web_view = WebKit.WebView()
            if anchor:
                web_view.connect("load-changed", self._on_load_changed)
            web_view.load_html(help_content.render_help_html(), f"file://{data_dir}/")
            toolbar.set_content(web_view)
        except (ValueError, ImportError):
            status = Adw.StatusPage(
                icon_name="help-about-symbolic",
                title=_("Could not open the built-in manual"),
            )
            toolbar.set_content(status)

        self.set_content(toolbar)

    def _on_load_changed(self, web_view, load_event) -> None:
        from gi.repository import WebKit

        if load_event == WebKit.LoadEvent.FINISHED:
            script = f"document.getElementById({self._anchor!r})?.scrollIntoView();"
            web_view.evaluate_javascript(script, -1, None, None, None, None, None)


class ImportSelectionDialog(Adw.Dialog):
    """Lists the apps found in an import JSON with a switch per item —
    nothing is imported without explicit selection."""

    def __init__(self, app_entries: list[dict], on_confirm):
        super().__init__(title=_("Choose what to import"), content_width=440, content_height=560)
        self._app_entries = app_entries
        self._on_confirm = on_confirm
        self._switches: list[Adw.SwitchRow] = []

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        page = Adw.PreferencesPage()
        title = ngettext("%(n)d site found", "%(n)d sites found", len(app_entries)) % {"n": len(app_entries)}
        group = Adw.PreferencesGroup(
            title=title,
            description=_("Uncheck anything you don't want to import."),
        )
        for entry in app_entries:
            name = entry.get("name") or _("(no name)")
            url = entry.get("url") or ""
            row = Adw.SwitchRow(title=name, subtitle=url, active=True)
            group.add(row)
            self._switches.append(row)
        page.add(group)

        actions = Adw.PreferencesGroup()
        import_button = Gtk.Button(label=_("Import selected"))
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
    """Page with the list of web apps already created."""

    def __init__(self, nav_view: Adw.NavigationView):
        super().__init__(title="Casca")
        self._nav_view = nav_view

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()

        app_icon = Gtk.Image.new_from_icon_name("io.github.oliverhubtech_source.Casca")
        app_icon.set_pixel_size(20)
        header.pack_start(app_icon)

        menu = Gio.Menu()
        menu.append(_("User guide"), "page.help")
        menu.append(_("About Casca"), "page.about")
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text=_("Menu"))
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

        create_actions = Gio.SimpleActionGroup()
        for name, handler in (
            ("app", self._on_create_app),
            ("package", self._on_create_package),
            ("environment", self._on_create_environment),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", handler)
            create_actions.add_action(action)
        self.insert_action_group("create", create_actions)

        self._page = Adw.PreferencesPage()
        self._groups: list[Adw.PreferencesGroup] = []
        toolbar.set_content(self._page)

        bottom_bar = Gtk.CenterBox(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_bar.set_margin_top(12)
        bottom_bar.set_margin_bottom(12)
        bottom_bar.set_margin_start(12)
        bottom_bar.set_margin_end(12)

        store_button = Gtk.Button(icon_name="org.gnome.Software-symbolic", tooltip_text=_("Store"))
        store_button.add_css_class("pill")
        store_button.connect("clicked", self._on_open_store_page)
        bottom_bar.set_start_widget(store_button)

        create_button = Gtk.MenuButton(tooltip_text=_("Create a new app, package or environment"))
        create_button.set_child(Adw.ButtonContent(icon_name="list-add-symbolic", label=_("Create")))
        create_button.add_css_class("suggested-action")
        create_button.add_css_class("pill")
        create_menu = Gio.Menu()
        create_menu.append(_("App"), "create.app")
        create_menu.append(_("Package"), "create.package")
        create_menu.append(_("Environment"), "create.environment")
        create_button.set_menu_model(create_menu)
        bottom_bar.set_center_widget(create_button)

        import_export_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        import_export_box.add_css_class("linked")

        import_button = Gtk.Button(icon_name="document-open-symbolic", tooltip_text=_("Import apps"))
        import_button.connect("clicked", self._on_import)
        import_export_box.append(import_button)

        export_button = Gtk.Button(icon_name="document-save-symbolic", tooltip_text=_("Export apps"))
        export_button.connect("clicked", self._on_export)
        import_export_box.append(export_button)

        bottom_bar.set_end_widget(import_export_box)
        toolbar.add_bottom_bar(bottom_bar)

        self.set_child(toolbar)

        self.refresh()

    def _on_create_app(self, *_args) -> None:
        editor = EditorPage(self._nav_view, on_saved=self.refresh)
        self._nav_view.push(editor)

    def _on_create_package(self, *_args) -> None:
        editor = PackageEditorPage(self._nav_view, on_saved=self.refresh)
        self._nav_view.push(editor)

    def _on_create_environment(self, *_args) -> None:
        editor = EnvironmentEditorPage(self._nav_view, on_saved=self.refresh)
        self._nav_view.push(editor)

    def _on_open_store_page(self, *_args) -> None:
        window = StoreWindow(self.get_ancestor(Gtk.Window), self._nav_view, on_refresh_list=self.refresh)
        window.present()

    def _on_open_help(self, *_args) -> None:
        window = HelpWindow(self.get_ancestor(Gtk.Window))
        window.present()

    def _on_open_about(self, *_args) -> None:
        app = self.get_root().get_application()
        updater.check_and_notify(app)

        # Channel word to the left of the number ("Beta 1.2.0") — packaged installs
        # (Flatpak/Snap/RPM/COPR) have no branch info, so they're always "Release".
        version_label = f"{updater.release_channel()} {__version__}"

        comments = _("Turns any website into a GNOME app.")
        latest = updater.cached_latest_version()
        if latest and updater.is_newer(latest, __version__):
            comments += "\n\n" + _(
                "Version %(latest)s is available — an update notification with a way to update just popped up."
            ) % {"latest": latest}

        about = Adw.AboutDialog(
            application_name="Casca",
            application_icon="io.github.oliverhubtech_source.Casca",
            version=version_label,
            developer_name="OliverHub",
            comments=comments,
            website="https://github.com/oliverhubtech-source/casca",
            issue_url="https://github.com/oliverhubtech-source/casca/issues",
            license_type=Gtk.License.MIT_X11,
            release_notes_version="1.3.0",
            release_notes=(
                "<p>" + _(
                    "The Store is now the Casca Store, in the style of GNOME Software: a featured "
                    "apps carousel, colorful category tiles, Editor's Choice, and a page for each "
                    "app with usage tags, the Bronze/Silver/Gold Casca seal, estimated disk "
                    "savings, possible PC access and security info."
                ) + "</p>"
                "<p>" + _(
                    "A region selector next to the search detects your country automatically and "
                    "filters marketplaces and news to your region — or choose Global to see "
                    "everything. All of it translated into the 20 supported languages."
                ) + "</p>"
            ),
        )
        about.add_link(_("Source Code"), "https://github.com/oliverhubtech-source/casca")
        about.present(self)

    def _toast(self, message: str) -> None:
        root = self.get_ancestor(Gtk.Window)
        if isinstance(root, CascaWindow):
            root.toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def _on_export(self, *_args) -> None:
        if not entries.list_apps():
            self._toast(_("No app created yet to export."))
            return
        dialog = Gtk.FileDialog(title=_("Export apps"), initial_name="casca-apps.json")
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
            self._toast(_("Error exporting: %(error)s") % {"error": error})
            return
        self._toast(
            ngettext("%(count)d app exported to %(name)s.", "%(count)d apps exported to %(name)s.", count)
            % {"count": count, "name": path.name}
        )

    def _on_import(self, *_args) -> None:
        dialog = Adw.AlertDialog(
            heading=_("Import from where?"),
            body=_('Choose a local .json file or a URL (e.g. a GitHub "raw" link).'),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("url", _("From a URL"))
        dialog.add_response("file", _("Local file"))
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
        dialog = Gtk.FileDialog(title=_("Import apps"))
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
            self._toast(_("Error reading the file: %(error)s") % {"error": error})
            return
        self._open_import_selection(data)

    def _on_import_pick_url(self) -> None:
        dialog = Adw.AlertDialog(
            heading=_("Import from a URL"),
            body=_('Paste the JSON file\'s "raw" link (e.g. from a GitHub repository).'),
        )
        entry = Adw.EntryRow(title="URL")
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("fetch", _("Fetch"))
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
            self._toast(_("Enter a URL."))
            return
        self._toast(_("Fetching file…"))
        threading.Thread(target=self._fetch_import_url_worker, args=(url,), daemon=True).start()

    def _fetch_import_url_worker(self, url: str) -> None:
        try:
            data = entries.fetch_import_payload(url)
        except ValueError as error:
            GLib.idle_add(self._toast, _("Error downloading: %(error)s") % {"error": error})
            return
        GLib.idle_add(self._open_import_selection, data)

    def _open_import_selection(self, data: bytes) -> bool:
        try:
            app_entries = entries.parse_import_candidates(data)
        except ValueError as error:
            self._toast(_("Error importing: %(error)s") % {"error": error})
            return False
        if not app_entries:
            self._toast(_("No app found in the file."))
            return False
        dialog = ImportSelectionDialog(app_entries, on_confirm=self._on_import_selection_confirmed)
        dialog.present(self)
        return False

    def _on_import_selection_confirmed(self, app_entries: list[dict], selected_indices: set[int]) -> None:
        if not selected_indices:
            self._toast(_("Nothing selected to import."))
            return
        result = entries.import_selected(app_entries, selected_indices)
        self.refresh()
        if result.failures:
            self._show_import_errors(result)
        else:
            self._toast(
                ngettext("%(n)d app imported.", "%(n)d apps imported.", len(result.created))
                % {"n": len(result.created)}
            )

    def _show_import_errors(self, result: entries.ImportResult) -> None:
        lines = "\n".join(
            _("• %(name)s: %(reason)s") % {"name": failure.name, "reason": failure.reason}
            for failure in result.failures
        )
        dialog = Adw.AlertDialog(
            heading=_("%(created)d imported, %(failed)d with errors")
            % {"created": len(result.created), "failed": len(result.failures)},
            body=_('Review and adjust manually via the "Create" button:\n\n%(lines)s') % {"lines": lines},
        )
        dialog.add_response("ok", _("Got it"))
        dialog.present(self)

    def refresh(self) -> None:
        for group in self._groups:
            self._page.remove(group)
        self._groups.clear()

        apps = entries.list_apps()
        packages = entries.list_packages()
        environments = entries.list_environments()

        if not apps and not packages and not environments:
            status = Adw.StatusPage(
                icon_name="io.github.oliverhubtech_source.Casca",
                title=_("No web apps yet"),
                description=_("Tap “Create” to make your first app, or open the Store for ready-made sites."),
            )
            group = Adw.PreferencesGroup()
            group.add(status)
            self._page.add(group)
            self._groups.append(group)
            return

        if apps:
            group = Adw.PreferencesGroup(title=_("My web apps"))
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
            pkg_group = Adw.PreferencesGroup(title=_("Installed packages"))
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

        if environments:
            env_group = Adw.PreferencesGroup(title=_("Environments"))
            for env in environments:
                row = Adw.ActionRow(title=env.name, subtitle=env.description or None)
                row.add_prefix(_row_leading_widget(env.icon_path or env.banner_path))

                edit_button = Gtk.Button(icon_name="document-edit-symbolic", valign=Gtk.Align.CENTER)
                edit_button.add_css_class("flat")
                edit_button.connect("clicked", self._on_edit_environment, env)

                delete_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
                delete_button.add_css_class("flat")
                delete_button.connect("clicked", self._on_delete_environment, env)

                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                box.append(edit_button)
                box.append(delete_button)
                row.add_suffix(box)
                env_group.add(row)
            self._page.add(env_group)
            self._groups.append(env_group)

    def _on_edit(self, _button: Gtk.Button, app: entries.WebApp) -> None:
        editor = EditorPage(self._nav_view, on_saved=self.refresh, existing=app)
        self._nav_view.push(editor)

    def _on_delete(self, _button: Gtk.Button, app: entries.WebApp) -> None:
        dialog = Adw.AlertDialog(
            heading=_("Delete “%(name)s”?") % {"name": app.name},
            body=_("The shortcut will be removed from the applications menu and the desktop, if it exists."),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete"))
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
            heading=_("Delete package “%(name)s”?") % {"name": package.name},
            body=ngettext(
                "Removes the shortcut and the %(n)d app inside it (%(names)s).",
                "Removes the shortcut and the %(n)d apps inside it (%(names)s).",
                len(package.app_names),
            )
            % {"n": len(package.app_names), "names": ", ".join(package.app_names)},
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete"))
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

    def _on_edit_environment(self, _button: Gtk.Button, env: entries.EnvironmentInfo) -> None:
        editor = EnvironmentEditorPage(self._nav_view, on_saved=self.refresh, existing=env)
        self._nav_view.push(editor)

    def _on_delete_environment(self, _button: Gtk.Button, env: entries.EnvironmentInfo) -> None:
        dialog = Adw.AlertDialog(
            heading=_("Delete environment “%(name)s”?") % {"name": env.name},
            body=_("Its apps and packages are not removed — they move back to the Default environment."),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_delete_environment_response, env)
        dialog.present(self)

    def _on_delete_environment_response(
        self, _dialog: Adw.AlertDialog, response: str, env: entries.EnvironmentInfo
    ) -> None:
        if response == "delete":
            entries.delete_environment(env.slug)
            self.refresh()


class CascaWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application):
        super().__init__(application=application, title="Casca", default_width=480, default_height=640)

        self.toast_overlay = Adw.ToastOverlay()
        nav_view = Adw.NavigationView()
        nav_view.push(ListPage(nav_view))
        self.toast_overlay.set_child(nav_view)
        self.set_content(self.toast_overlay)
