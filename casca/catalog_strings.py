"""Translatable labels that live as data, not code.

The values of the ``kind``/``country``/``package`` fields in
``data/store_catalog.json`` are shown as section titles in the Store (see
``window.py``'s ``_group_icon_widget``/``_rebuild_rows``), so they need
translation just like any other UI string. ``xgettext`` cannot scan JSON, so
this module exists purely to give it something to find — it is never
imported or executed for its own sake.

Keep this list in sync with the ``kind``/``country``/``package`` values used
in ``data/store_catalog.json``.
"""

from .i18n import _

_("Artificial Intelligence")
_("Cloud Computing")
_("Conversion & Sharing")
_("Creativity")
_("Finance")
_("Marketplace")
_("Messenger")
_("Music Streaming")
_("News")
_("PDF")
_("Productivity")
_("Search Engine")
_("Security")
_("Social Network")
_("Utility")
_("Video Streaming")

_("Argentina")
_("Brazil")
_("Chile")
_("Colombia")
_("Europe")
_("France")
_("Germany")
_("International")
_("Mexico")
_("Netherlands")
_("Paraguay")
_("Poland")
_("Spain")
_("United Kingdom")
_("United States")
_("Uruguay")

_("Google Workspace")
_("Microsoft 365")
_("Social Media")
_("YouTube")
