Name:           casca
Version:        1.4.0
Release:        1%{?dist}
Summary:        Turn any website into a native GNOME app

License:        MIT
URL:            https://github.com/oliverhubtech-source/casca
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  desktop-file-utils
BuildRequires:  appstream

Requires:       python3-gobject
Requires:       python3-requests
Requires:       python3-pillow
Requires:       gtk4
Requires:       libadwaita
# WebKitGTK powers each web app's own window (colored title bar, no browser
# chrome). Without it Casca still works, falling back to launching external
# browsers in app mode.
Recommends:     webkitgtk6.0

%description
Casca turns any website into a native GNOME app: pick the address, Casca
fetches the icon automatically and creates a shortcut in the applications
menu (and, optionally, on the desktop). Each app opens in its own window,
with no leftover browser bar — including a title bar colored to match the
site's icon.

Main features: a store with hundreds of ready-made sites; packages that
group several related sites behind one icon; mobile mode with device
simulation; import/export of apps via JSON; and per-app browser
profiles/accounts for isolated logins.

%prep
%autosetup

%build
# Pure Python + data, nothing to compile — rpmbuild's build-root policy
# byte-compiles the installed .py files automatically.

%install
appdir=%{buildroot}%{_datadir}/casca
install -d "$appdir"
cp -r casca "$appdir/casca"
install -pm644 run.py run_webview.py run_package.py "$appdir/"

# casca/browsers.py and casca/entries.py locate run_webview.py/run_package.py
# as siblings of the installed "casca" package directory (same layout as a
# checkout run via install.sh) — keep run.py, run_webview.py and
# run_package.py alongside %{_datadir}/casca/casca, not inside it.
install -d %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/casca <<'EOF'
#!/bin/sh
exec python3 %{_datadir}/casca/run.py "$@"
EOF
chmod 755 %{buildroot}%{_bindir}/casca

install -Dpm644 casca/data/io.github.oliverhubtech_source.Casca.desktop \
    %{buildroot}%{_datadir}/applications/io.github.oliverhubtech_source.Casca.desktop
install -Dpm644 casca/data/io.github.oliverhubtech_source.Casca.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/io.github.oliverhubtech_source.Casca.metainfo.xml
install -Dpm644 casca/data/icons/io.github.oliverhubtech_source.Casca.png \
    %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/io.github.oliverhubtech_source.Casca.png

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/io.github.oliverhubtech_source.Casca.desktop
appstreamcli validate --pedantic --explain %{buildroot}%{_datadir}/metainfo/io.github.oliverhubtech_source.Casca.metainfo.xml

%files
%license LICENSE
%doc README.md
%{_bindir}/casca
%{_datadir}/casca/
%{_datadir}/applications/io.github.oliverhubtech_source.Casca.desktop
%{_datadir}/metainfo/io.github.oliverhubtech_source.Casca.metainfo.xml
%{_datadir}/icons/hicolor/256x256/apps/io.github.oliverhubtech_source.Casca.png

%changelog
* Mon Jul 13 2026 OliverHub <282591028+oliverhubtech-source@users.noreply.github.com> - 1.4.0-1
- Environments: group any number of apps and packages under a shared context
  (name, banner, icon, notes and creation defaults), with one launcher that
  opens a window listing everything inside it
- The Create button is now a menu: App, Package or Environment
- The main list shows environments alongside apps and packages, ready to edit
  or remove
* Sat Jul 11 2026 OliverHub <282591028+oliverhubtech-source@users.noreply.github.com> - 1.3.0-1
- Casca Store rebuilt in the GNOME Software style: featured carousel, colorful
  categories, Editor's Choice and a detail page per app (usage tags, Casca seal,
  disk savings, PC access, security info, company pages)
- Region selector next to the search filters marketplaces/news by country
- All new Store strings translated into the 20 supported languages
* Fri Jul 10 2026 OliverHub <282591028+oliverhubtech-source@users.noreply.github.com> - 1.2.0-1
- Background update check with system notification and one-click update
- About dialog: license, source link, release channel, "What's New" page
* Thu Jul 09 2026 OliverHub <282591028+oliverhubtech-source@users.noreply.github.com> - 1.1.0-1
- 20-language i18n (gettext), contextual help buttons and a redesigned manual
* Wed Jul 08 2026 OliverHub <282591028+oliverhubtech-source@users.noreply.github.com> - 1.0.0-1
- First public release of Casca
