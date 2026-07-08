"""Perfis de dispositivos para simular quando o app abre em modo mobile."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    key: str
    label: str
    user_agent: str
    width: int
    height: int


DEVICES: tuple[Device, ...] = (
    Device(
        "pixel-8",
        "Google Pixel 8",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
        412,
        915,
    ),
    Device(
        "iphone-15-pro",
        "iPhone 15 Pro",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        393,
        852,
    ),
    Device(
        "iphone-se",
        "iPhone SE",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        375,
        667,
    ),
    Device(
        "galaxy-s23",
        "Samsung Galaxy S23",
        "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
        360,
        780,
    ),
    Device(
        "ipad",
        "iPad",
        "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        810,
        1080,
    ),
)

DEFAULT_DEVICE_KEY = DEVICES[0].key


def find_device(key: str | None) -> Device:
    for device in DEVICES:
        if device.key == key:
            return device
    return DEVICES[0]


@dataclass(frozen=True)
class StandardSize:
    key: str
    label: str
    width: int
    height: int


STANDARD_SIZES: tuple[StandardSize, ...] = (
    StandardSize("small", "Pequena (800×600)", 800, 600),
    StandardSize("medium", "Média (1024×768)", 1024, 768),
    StandardSize("laptop", "Notebook (1280×800)", 1280, 800),
    StandardSize("laptop-hd", "Notebook HD (1366×768)", 1366, 768),
    StandardSize("large", "Grande (1600×900)", 1600, 900),
    StandardSize("full-hd", "Full HD (1920×1080)", 1920, 1080),
)


def find_standard_size(key: str | None) -> StandardSize:
    for size in STANDARD_SIZES:
        if size.key == key:
            return size
    return STANDARD_SIZES[0]
