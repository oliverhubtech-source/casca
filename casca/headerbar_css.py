"""CSS que colore a barra de título com a cor dominante do ícone do site — usado tanto
pelo editor principal quanto pelos runtimes standalone (janela própria de um app e
launcher de pacote), por isso fica num módulo só com dependências de stdlib."""


def build_header_css(css_class: str, color: str, text_color: str) -> str:
    return (
        f"headerbar.{css_class} {{ background: {color}; color: {text_color}; }}"
        f"headerbar.{css_class} windowcontrols button {{ color: {text_color}; }}"
    )
