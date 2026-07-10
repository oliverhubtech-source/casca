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
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

_header_class_counter = itertools.count()

from . import browsers, devices, entries, help_content, icons, presets, profiles, social_icons, store
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

    def _load_existing(self, app: entries.WebApp) -> None:
        self.set_title(_("Edit app"))
        self._save_button.set_label(_("Save changes"))
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


class StoreWindow(Adw.ApplicationWindow):
    """Store: its own window with a catalog of ready-made sites, grouped by Company/Type/Package."""

    def __init__(self, parent: Adw.ApplicationWindow, nav_view: Adw.NavigationView, on_refresh_list):
        super().__init__(
            application=parent.get_application(),
            transient_for=parent,
            default_width=560,
            default_height=760,
            title=_("Store"),
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
            ("company", _("Company")),
            ("kind", _("Type")),
            ("package", _("Package")),
            ("marketplace", _("Marketplace")),
            ("news", _("News")),
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

        self._search_entry = Gtk.SearchEntry(placeholder_text=_("Search by name…"))
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
            self._toast(_("Could not set an icon for %(name)s.") % {"name": package_name})
            return

        try:
            entries.create_package(package_name, sub_apps, package_icon)
        except ValueError as error:
            self._toast(_("Error installing package: %(error)s") % {"error": error})
            return

        self._on_refresh_list()
        self._toast(
            ngettext(
                "Package “%(name)s” installed with %(n)d app.",
                "Package “%(name)s” installed with %(n)d apps.",
                len(items),
            )
            % {"name": package_name, "n": len(items)}
        )

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
                title=_("Nothing here yet"),
                description=_("Check the local catalog or your internet connection."),
            )
            group = Adw.PreferencesGroup()
            group.add(status)
            self._page.add(group)
            self._current_group = group
            return

        grouped = store.group_by(items_pool, group_key)
        group = Adw.PreferencesGroup()
        for key, items in grouped.items():
            subtitle = ngettext("%(n)d site", "%(n)d sites", len(items)) % {"n": len(items)}
            expander = Adw.ExpanderRow(title=_(key), subtitle=subtitle)
            expander.add_prefix(self._group_icon_widget(key))
            if group_key == "package" and key != _("Independent apps"):
                install_button = Gtk.Button(
                    label=_("Install full package"), valign=Gtk.Align.CENTER
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
        """Only fetches/decodes a group's icons (base64 -> PNG on disk) the first
        time it's expanded — avoids doing this for every catalog item (including
        groups the user never opens) every time the Store is opened or the tab is
        switched."""
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
        """Builds the row with a lightweight placeholder (initials Avatar, no disk access).
        The real icon (decoded from the catalog's base64) only loads once the group
        is expanded — see `_on_group_expanded`."""
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
    """Casca's user guide, rendered from help_content.py in the app's active language."""

    def __init__(self, parent: Adw.ApplicationWindow):
        super().__init__(
            application=parent.get_application(),
            transient_for=parent,
            default_width=780,
            default_height=760,
            title=_("Casca Manual"),
        )

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        data_dir = Path(__file__).parent / "data"
        try:
            gi.require_version("WebKit", "6.0")
            from gi.repository import WebKit

            web_view = WebKit.WebView()
            web_view.load_html(help_content.render_help_html(), f"file://{data_dir}/")
            toolbar.set_content(web_view)
        except (ValueError, ImportError):
            status = Adw.StatusPage(
                icon_name="help-about-symbolic",
                title=_("Could not open the built-in manual"),
            )
            toolbar.set_content(status)

        self.set_content(toolbar)


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

        create_button = Gtk.Button(tooltip_text=_("Create a new web app"))
        create_button.set_child(Adw.ButtonContent(icon_name="list-add-symbolic", label=_("Create")))
        create_button.add_css_class("suggested-action")
        create_button.add_css_class("pill")
        create_button.connect("clicked", self._on_add)
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
            comments=_("Turns any website into a GNOME app."),
        )
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

        if not apps and not packages:
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


class CascaWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application):
        super().__init__(application=application, title="Casca", default_width=480, default_height=640)

        self.toast_overlay = Adw.ToastOverlay()
        nav_view = Adw.NavigationView()
        nav_view.push(ListPage(nav_view))
        self.toast_overlay.set_child(nav_view)
        self.set_content(self.toast_overlay)
