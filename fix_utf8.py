# -*- coding: utf-8 -*-
"""
Corrector de mojibake UTF-8 para archivos frontend de Turnix.
Usa enfoque programático: calcula las secuencias mojibake en tiempo de ejecución
para evitar problemas de codificación en el propio script.
"""
import glob
import os
import re


def compute_replacements():
    """
    Calcula pares (mojibake, correcto) codificando cada carácter correcto en UTF-8
    y decodificando como cp1252 (Windows-1252) o latin-1 como fallback.
    """
    correct_chars = [
        # Vocales minúsculas con tilde
        'á', 'é', 'í', 'ó', 'ú',
        # Vocales mayúsculas con tilde
        'Á', 'É', 'Í', 'Ó', 'Ú',
        # Ñ
        'ñ', 'Ñ',
        # Ü
        'ü', 'Ü',
        # Puntuación especial
        '…', '—', '–', '×',
        # Emojis (base, sin variation selector)
        '🏢', '📋', '👤', '👥',
        '🟢', '🔴', '🟠', '⚪',
        '🤖', '🔑', '💬',
        '✂', '⚙', 'ℹ',
        '✅', '✕', '✗',
        '📅', '📊', '❌', '🔍',
        '🗓', '🏷',
    ]
    # Emojis con variation selector U+FE0F (se codifican completos)
    combined_emojis = [
        '✂️', '⚙️', 'ℹ️', '⚠️', '🗓️', '🏷️',
    ]

    reps = []
    seen = set()

    for char in correct_chars + combined_emojis:
        utf8_bytes = char.encode('utf-8')
        for encoding in ('cp1252', 'latin-1'):
            try:
                mojibake = utf8_bytes.decode(encoding)
                key = mojibake
                if mojibake != char and key not in seen:
                    seen.add(key)
                    reps.append((mojibake, char))
                break  # primer encoding exitoso es suficiente
            except UnicodeDecodeError:
                pass  # cp1252 falla en bytes no definidos, probar latin-1

    # Ordenar de mayor a menor longitud para evitar reemplazos parciales
    reps.sort(key=lambda x: -len(x[0]))
    return reps


REPLACEMENTS = compute_replacements()


def fix_mojibake(fpath):
    """Corrige secuencias mojibake en un archivo."""
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            original = f.read()
    except Exception as e:
        print(f'  ERROR leyendo {fpath}: {e}')
        return False

    content = original
    for bad, good in REPLACEMENTS:
        content = content.replace(bad, good)

    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def fix_unicode_escapes(fpath):
    """
    Convierte secuencias literales \\uXXXX (escritas por PowerShell) a caracteres reales.
    Solo afecta a puntos de código del Latin Extended (acentos españoles) y signos comunes.
    """
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            original = f.read()
    except Exception:
        return False

    def replace_escape(m):
        cp = int(m.group(1), 16)
        # Latin-1 Supplement + Latin Extended-A/B + signos tipográficos frecuentes
        if (0x00C0 <= cp <= 0x024F) or cp in (0x2014, 0x2026, 0x2715, 0x00D7):
            return chr(cp)
        return m.group(0)

    content = re.sub(r'\\u([0-9a-fA-F]{4})', replace_escape, original)

    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def fix_business_config_accents(fpath):
    """Añade tildes que faltan en las etiquetas de BusinessConfig.jsx."""
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            original = f.read()
    except Exception:
        return False

    fixes = [
        ('<label>Descripcion</label>', '<label>Descripción</label>'),
        ('<label>Telefono</label>',    '<label>Teléfono</label>'),
        ('<label>Direccion</label>',   '<label>Dirección</label>'),
    ]
    content = original
    for bad, good in fixes:
        content = content.replace(bad, good)

    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    patterns = [
        'frontend/src/**/*.jsx',
        'frontend/src/**/*.js',
        'frontend/src/**/*.css',
        'frontend/index.html',
    ]

    files = []
    for p in patterns:
        files += glob.glob(os.path.join(base, p), recursive=True)

    print(f'Revisando {len(files)} archivos...')
    print()

    fixed = 0
    for fpath in sorted(files):
        changed = False

        # Paso 1: corregir mojibake general en todos los archivos
        if fix_mojibake(fpath):
            changed = True

        # Paso 2: Tenants.jsx puede tener secuencias literales \\uXXXX
        if fpath.endswith('Tenants.jsx'):
            if fix_unicode_escapes(fpath):
                changed = True

        # Paso 3: BusinessConfig.jsx tiene labels sin tilde
        if fpath.endswith('BusinessConfig.jsx'):
            if fix_business_config_accents(fpath):
                changed = True

        if changed:
            rel = os.path.relpath(fpath, base)
            print(f'  Corregido: {rel}')
            fixed += 1

    print()
    print(f'Total archivos corregidos: {fixed} de {len(files)} revisados.')

    # Mostrar tabla de reemplazos calculados (debug)
    print()
    print(f'Patrones mojibake detectados: {len(REPLACEMENTS)}')
    for bad, good in REPLACEMENTS[:10]:
        print(f'  {repr(bad):25s} -> {repr(good)}')
    if len(REPLACEMENTS) > 10:
        print(f'  ... y {len(REPLACEMENTS)-10} más')


if __name__ == '__main__':
    main()
