"""CSS that colors the title bar with the site icon's dominant color — used both
by the main editor and the standalone runtimes (an app's own window and the
package launcher), which is why it lives in its own module with only stdlib deps."""


def build_header_css(css_class: str, color: str, text_color: str) -> str:
    return (
        f"headerbar.{css_class} {{ background: {color}; color: {text_color}; }}"
        f"headerbar.{css_class} windowcontrols button {{ color: {text_color}; }}"
    )
