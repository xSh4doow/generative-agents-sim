"""Gera output/demo.gif — uma "gravação" de terminal da simulação em modo mock.

Não usa asciinema (que exige TTY interativo). Em vez disso, executa a simulação,
captura a saída verbose e renderiza frames de um terminal estilizado com PIL,
revelando as linhas progressivamente (efeito de scroll), e salva como GIF.

Uso:
    python make_demo_gif.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

# ---- aparência do terminal ------------------------------------------------ #
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 17
COLS = 92
VISIBLE_ROWS = 26
PAD = 22
TITLEBAR = 34
LINE_H = 23

BG = (15, 15, 18)
FG = (220, 222, 228)
DIM = (130, 134, 145)
CYAN = (90, 190, 220)
GREEN = (95, 200, 130)
YELLOW = (230, 200, 110)
BLUE = (110, 170, 235)
MAGENTA = (200, 150, 230)
TITLE_BG = (32, 33, 40)


EMOJI_MAP = {
    "🏘️": ">", "🏘": ">", "📊": "##", "✅": "✓", "⚠️": "!", "⚠": "!",
    "❌": "x", "🎬": ">", "️": "",
}


def sanitize(line: str) -> str:
    for k, v in EMOJI_MAP.items():
        line = line.replace(k, v)
    # remove qualquer outro emoji/símbolo fora do plano básico (evita tofu)
    return "".join(c for c in line if ord(c) < 0x2500 or c in "✓—↔")


def color_for(line: str) -> tuple:
    s = line.strip()
    if s.startswith("==="):
        return YELLOW
    if "📊" in line or "AVALIAÇÃO" in line:
        return YELLOW
    if line.startswith("[REFLEXÃO]") or "[REFLEXÃO]" in line:
        return MAGENTA
    if ">>" in line:
        return GREEN
    if "✅" in line or "similaridade" in line or "Taxa final" in line:
        return GREEN
    if line.startswith("[") and "↔" in line:
        return CYAN
    if line.lstrip().startswith("---") or line.startswith("🏘️"):
        return BLUE
    if "—" in line and ("Dia" in line):
        return FG
    return FG


def run_and_capture() -> list[str]:
    print("Rodando simulação mock para capturar saída...")
    proc = subprocess.run(
        [sys.executable, "main.py", "--mode", "mock", "--verbose"],
        capture_output=True, text=True,
    )
    raw = proc.stdout.splitlines()
    return curate(raw)


def curate(lines: list[str]) -> list[str]:
    """Seleciona uma narrativa enxuta: setup, alguns dias/conversas com
    propagação, uma reflexão, e o bloco de avaliação final."""
    out: list[str] = []
    convs_kept = 0
    in_eval = False
    i = 0
    while i < len(lines):
        ln = lines[i]
        if "AVALIAÇÃO" in ln or in_eval:
            in_eval = True
            out.append(ln)
            i += 1
            continue
        # setup / seed
        if ln.strip().startswith("+ ") or ">> info-semente" in ln or ln.startswith("🏘️"):
            out.append(ln)
        elif "Planejando Dia" in ln:
            out.append(ln)
        elif ln.startswith("=== Dia"):
            # mantém só alguns headers pra não inflar
            out.append(ln)
        elif ln.startswith("[") and "↔" in ln:
            if convs_kept < 5:
                out.append(ln)
                # inclui os turnos seguintes (linhas indentadas) + propagação
                j = i + 1
                while j < len(lines) and (lines[j].startswith("    ") or ">>" in lines[j]):
                    out.append(lines[j])
                    j += 1
                convs_kept += 1
                i = j
                continue
        elif ln.startswith("[REFLEXÃO]") and convs_kept >= 1:
            out.append(ln)
            j = i + 1
            cnt = 0
            while j < len(lines) and lines[j].startswith("    ") and cnt < 2:
                out.append(lines[j])
                j += 1
                cnt += 1
            i = j
            continue
        i += 1
    return out


def wrap_lines(lines: list[str]) -> list[str]:
    wrapped: list[str] = []
    for ln in lines:
        ln = sanitize(ln)
        if not ln:
            wrapped.append("")
            continue
        indent = len(ln) - len(ln.lstrip())
        pieces = textwrap.wrap(ln, width=COLS, subsequent_indent=" " * (indent + 2)) or [""]
        wrapped.extend(pieces)
    return wrapped


def render(lines: list[str], out_path: str) -> None:
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    font_b = ImageFont.truetype(FONT_BOLD, FONT_SIZE)
    char_w = font.getbbox("M")[2]
    width = PAD * 2 + char_w * COLS
    height = TITLEBAR + PAD * 2 + LINE_H * VISIBLE_ROWS

    def make_frame(visible: list[str]) -> Image.Image:
        img = Image.new("RGB", (width, height), BG)
        d = ImageDraw.Draw(img)
        # title bar
        d.rectangle([0, 0, width, TITLEBAR], fill=TITLE_BG)
        for k, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
            d.ellipse([PAD + k * 26, 11, PAD + k * 26 + 13, 24], fill=c)
        d.text((width // 2 - 150, 8), "simulação social — modo mock", font=font, fill=DIM)
        # body
        y = TITLEBAR + PAD
        for ln in visible:
            col = color_for(ln)
            f = font_b if (ln.startswith("===") or "AVALIAÇÃO" in ln) else font
            d.text((PAD, y), ln, font=f, fill=col)
            y += LINE_H
        return img

    wrapped = wrap_lines(lines)
    frames: list[Image.Image] = []
    durations: list[int] = []

    # revela linha a linha, viewport rola mantendo as últimas VISIBLE_ROWS
    for n in range(1, len(wrapped) + 1):
        shown = wrapped[:n][-VISIBLE_ROWS:]
        frames.append(make_frame(shown))
        last = wrapped[n - 1]
        # ritmo: conversas mais lentas, resto rápido
        if last.strip().startswith(("Helena:", "Roberto:", "Camila:", "Marcos:", "Júlia:")):
            durations.append(420)
        elif ">>" in last or "AVALIAÇÃO" in last:
            durations.append(650)
        elif last.startswith("==="):
            durations.append(300)
        else:
            durations.append(150)

    # segura o último frame
    frames.append(frames[-1])
    durations.append(2600)

    frames[0].save(
        out_path, save_all=True, append_images=frames[1:],
        duration=durations, loop=0, optimize=True, disposal=2,
    )
    print(f"✅ {out_path} — {len(frames)} frames, {width}×{height}px")


def main() -> int:
    lines = run_and_capture()
    if not lines:
        print("[ERRO] nenhuma saída capturada")
        return 1
    render(lines, "output/demo.gif")
    return 0


if __name__ == "__main__":
    sys.exit(main())
