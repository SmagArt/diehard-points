#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build.py — собрать index.html из исходника страницы.

Исходник (артефактная версия) — это фрагмент документа: <title>, <link>,
<style> и разметка подряд, без <head>/<body>. Здесь мы заворачиваем его в
полноценный HTML: title/link/style уезжают в <head>, остальное — в <body>.

    py build.py <исходник> [index.html]

Проверки, которые тут стоят не для красоты (на них уже ловились баги):
  * теги для <head> вырезаются с БАЛАНСОМ КАВЫЧЕК, а не первым встречным '>'.
    data-URI фавикона содержит '>' внутри значения href — нежадная регулярка
    рвала тег пополам, href оставался незакрытым, парсер съедал <style>,
    и страница уходила в прод без единого стиля;
  * после сборки head обязан содержать <style>, а тело — не начинаться с
    обрывка тега.
"""

import io
import re
import sys
from pathlib import Path

META = (
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    '<meta name="color-scheme" content="light dark">\n'
    '<meta name="description" content="Калькулятор баллов зачёта Die Hard: '
    'дистанция, темп и коэффициент.">'
)


def cut_tag(src: str, start_pat: str) -> tuple[str, str]:
    """Вырезать тег целиком: от начала до '>' ВНЕ кавычек. Вернуть (тег, остаток)."""
    m = re.search(start_pat, src)
    if not m:
        sys.exit(f"[ERR] не найден тег по шаблону {start_pat!r}")
    i, quote = m.start(), None
    while i < len(src):
        c = src[i]
        if quote:
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == ">":
            return src[m.start():i + 1], src[:m.start()] + src[i + 1:]
        i += 1
    sys.exit(f"[ERR] тег {start_pat!r} не закрыт — оборванный атрибут?")


def cut_block(src: str, tag: str) -> tuple[str, str]:
    m = re.search(rf"<{tag}>.*?</{tag}>", src, re.S)
    if not m:
        sys.exit(f"[ERR] не найден блок <{tag}>")
    return m.group(0), src[:m.start()] + src[m.end():]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "index.html"

    src = io.open(src_path, encoding="utf-8").read()
    title_tag, src = cut_tag(src, r"<title>")
    m = re.match(r"(.*?)</title>", src, re.S)
    title, src = m.group(1).strip(), src[m.end():]

    link_tag, src = cut_tag(src, r'<link rel="icon"')
    style_tag, src = cut_block(src, "style")
    body = src.strip()

    doc = (
        "<!doctype html>\n<html lang=\"ru\">\n<head>\n"
        f"{META}\n<title>{title}</title>\n{link_tag}\n{style_tag}\n"
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )

    # --- контроль качества сборки ---
    head = doc[doc.index("<head>"):doc.index("</head>")]
    body_start = doc[doc.index("<body>") + 6:][:400]
    problems = []
    if "<style>" not in head:
        problems.append("стили не попали в <head>")
    if 'rel="icon"' not in head:
        problems.append("фавикон не попал в <head>")
    if head.count('"') % 2:
        problems.append("нечётное число кавычек в <head> — оборванный атрибут")
    if body_start.lstrip().startswith(('">', "'>", ">")):
        problems.append("тело начинается с обрывка тега")
    for probe in ("Версия", "var TABLE", "id=\"female\""):
        if probe not in doc:
            problems.append(f"пропало из документа: {probe!r}")
    if problems:
        for p in problems:
            print("[ERR] " + p)
        return 1

    io.open(out_path, "w", encoding="utf-8", newline="\n").write(doc)
    print(f"[OK] {out_path.name}: {len(doc)} символов, проверки пройдены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
