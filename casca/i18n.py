"""Runtime translation setup (gettext) for Casca.

Bound against ``casca/data/locale`` so it works the same way whether the
package is run straight from a checkout or copied into a Flatpak's
``/app/lib/python*/site-packages`` prefix — both cases keep ``data/locale``
next to this file. ``install()`` must run before any other Casca module is
imported, since some modules call ``_()`` at import time (module-level
dicts/constants), and every other module does ``from .i18n import _`` —
that copies whatever ``_`` is bound to here at import time, so it has to
already be the real translation, not the placeholder.
"""

import gettext
import locale
import os

DOMAIN = "casca"
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "data", "locale")

_translation = gettext.NullTranslations()
_ = _translation.gettext
ngettext = _translation.ngettext


def install() -> None:
    global _translation, _, ngettext
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass
    _translation = gettext.translation(DOMAIN, LOCALE_DIR, fallback=True)
    _ = _translation.gettext
    ngettext = _translation.ngettext
