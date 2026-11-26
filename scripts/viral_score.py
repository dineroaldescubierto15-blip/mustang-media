"""Puntuació de potencial viral per a @mustangemotion.

Basada en l'estudi de 379 reels del nínxol Mustang (novembre 2026, vegeu docs/estudi-reels-virals.md).
Punt de partida: log10(visualitzacions). Cada senyal suma o resta segons l'efecte mesurat.
"""
import math
import re

CLASSIC = r"19[6-7]\d|\b6[4-9]\b|fastback|eleanor|classic|vintage|mach ?1|cobra jet|boss 302|restor|barn find"
AESTHETIC = r"night|sunset|golden hour|lights|glow|cinematic|aesthetic|rain|moon"
WEAK_FORMATS = r"drift|burnout|burn out|donut|sideways"
NOT_MUSTANG = r"camaro|challenger|charger|corvette only|supercars|nascar|v8 supercar"
NEVER = r"torino|mopar"


def score(post: dict, metrics: dict | None = None) -> tuple[float, list[str]]:
    m = metrics or {}
    cap = (post.get("caption") or "").lower()
    views = post.get("views") or post.get("videoPlayCount") or post.get("videoViewCount") or 0
    s = math.log10(max(views, 1))
    why = []

    def add(points: float, reason: str) -> None:
        nonlocal s
        s += points
        why.append(f"{'+' if points > 0 else ''}{points:g} {reason}")

    if re.search(CLASSIC, cap):
        add(0.35, "clàssic / icona")
    if re.search(AESTHETIC, cap):
        add(0.15, "estètica (nit, posta, llums)")
    b = m.get("brightness")
    if b is not None and b < 45:
        add(0.3, "imatge fosca / nocturna")
    oa = post.get("original_audio")
    if oa is True:
        add(0.1, "so original")
    shots = m.get("shots")
    if shots is not None:
        if 4 <= shots <= 8:
            add(0.15, "muntatge lleuger (4-8 plans)")
        elif 2 <= shots <= 3:
            add(-0.15, "2-3 plans")
        elif shots >= 9:
            add(-0.1, "massa talls (9+)")
    if m.get("text_1s"):
        add(0.05, "text en pantalla")
    if re.search(WEAK_FORMATS, cap):
        add(-0.3, "drift / burnout (rendeix poc)")
    if "?" in cap:
        add(-0.15, "text original amb pregunta")
    if re.search(NEVER, cap) or (re.search(NOT_MUSTANG, cap) and "mustang" not in cap):
        add(-2, "no és Mustang")
    return round(s, 3), why
