"""Idioma — español / inglés (Prompt de Diseño v5.3, sección 5).

Sin Qt a propósito: el núcleo (emulinks.core) también traduce sus mensajes de
log y se prueba sin pantalla. La interfaz decide el idioma al arrancar (lee
QSettings / idioma del sistema) y llama a set_language() antes de construir
cualquier widget. Por defecto, español.

Los textos viven en emulinks/locales/<código>.py, con las mismas claves en
todos los idiomas. Para revisar que no falte ninguna: check_translations().
"""

from emulinks.locales import en, es

LANGUAGES = {"es": "Español", "en": "English"}   # nombres sin traducir
STRINGS = {"es": es.STRINGS, "en": en.STRINGS}

LANG = "es"


def set_language(code: str) -> None:
    """Fija el idioma activo de la sesión. Se llama una sola vez al arrancar."""
    global LANG
    LANG = code if code in LANGUAGES else "es"


def tr(key: str, **kwargs) -> str:
    """Texto traducido. Si falta en el idioma activo usa español; si falta en
    ambos, muestra la clave (así se nota enseguida en pantalla)."""
    text = STRINGS.get(LANG, {}).get(key) or STRINGS["es"].get(key) or key
    return text.format(**kwargs) if kwargs else text


def tr_opt(key: str) -> str:
    """Como tr(), pero devuelve '' si la clave no existe (textos opcionales)."""
    return STRINGS.get(LANG, {}).get(key) or STRINGS["es"].get(key) or ""


def missing_translations() -> dict:
    """{idioma: [claves que faltan]} — usado por check_translations y los tests."""
    keys = {code: set(d) for code, d in STRINGS.items()}
    all_keys = set().union(*keys.values())
    return {code: sorted(all_keys - ks) for code, ks in keys.items() if all_keys - ks}


def check_translations() -> None:
    """Solo en desarrollo: avisa por consola qué claves faltan en algún idioma."""
    for code, missing in missing_translations().items():
        for k in missing:
            print(f"[i18n] Falta '{k}' en '{code}'")
