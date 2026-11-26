"""Generació de captions per a @mustangemotion.

Tres estils que roten (per poder comparar després quin funciona millor):
  A · Clàssic: model + pregunta curta de resposta fàcil
  B · Debat: puntuació de l'1 al 10
  C · Comunitat: crida a etiquetar-nos i a compartir
Màxim 5 hashtags (límit d'Instagram des de desembre de 2025).
"""
import hashlib
import re

STYLES = ["A", "B", "C"]
MAX_HASHTAGS = 5

# (paraules clau, nom per mostrar, hashtag) · de més específic a més general
MODELS = [
    (["dark horse", "darkhorse"], "Dark Horse", "darkhorse"),
    (["gt500", "gt 500", "gt-500", "super snake", "supersnake"], "Shelby GT500", "gt500"),
    (["gt350", "gt 350", "gt-350"], "Shelby GT350", "gt350"),
    (["mach 1", "mach1"], "Mach 1", "mach1"),
    (["bullitt"], "Bullitt", "bullitt"),
    (["boss 302", "boss302"], "Boss 302", "boss302"),
    (["eleanor"], "Eleanor", "eleanor"),
    (["rtr", "mustangrtr"], "Mustang RTR", "mustangrtr"),
    (["svt cobra", "terminator"], "SVT Cobra", "svtcobra"),
    (["foxbody", "fox body"], "Fox Body", "foxbody"),
    (["shelby"], "Shelby Mustang", "shelby"),
]
GENERATIONS = [
    (["s650"], "s650"), (["s550"], "s550"), (["s197"], "s197"), (["sn95"], "sn95"),
]

HOOKS = {
    "A": [
        "{car} 🐎 Clean or too aggressive? 👇",
        "{car} 🔥 Stock or modded? 👇",
        "{car} 👀 Would you change anything? 👇",
        "{car} 💨 Daily driver or weekend toy? 👇",
        "{car} 🔥 Dream car or overrated? 👇",
        "{car} 🖤 Perfect spec or not? 👇",
    ],
    "B": [
        "Rate this {car} from 1 to 10 👇🔥\nBe honest… 😏",
        "1 to 10: how clean is this {car}? 👇",
        "Out of 10, where does this {car} land? 👇🔥",
        "Give this {car} a score from 1 to 10 👇\nNo cap 🧢",
        "Rate the spec 1–10 👇🐎",
    ],
    "C": [
        "Would you daily this {car}? 🐎💨",
        "Would you take this {car} home? 🏠🐎",
        "Dream garage material? 🐎✨",
        "Who else wants this {car} in their driveway? 🙋‍♂️🐎",
        "Tag the friend who would drive this {car} every day 👀",
    ],
}

FOLLOW = {
    "A": "Follow @{account} for daily Mustang content! 🔥",
    "B": "Follow @{account} — the best Mustangs, every day 🐎",
    "C": "📸 Want to be featured? Tag @{account} in your Mustang posts!\nSend this to the friend who needs a Mustang 👀",
}

DISCLAIMER = "(If you're the owner and want this removed, DM us and we'll take it down)"


def _text(post: dict) -> str:
    return " ".join([post.get("caption") or "", " ".join(post.get("hashtags") or [])]).lower()


def _has(text: str, words: list[str]) -> bool:
    # inici de paraula, perquè "rtr" no coincideixi amb "portrait"
    return any(re.search(r"(?<![a-z0-9])" + re.escape(w), text) for w in words)


def detect(post: dict) -> tuple[str, list[str]]:
    """Retorna el nom del cotxe i els hashtags específics (model, generació)."""
    text = _text(post)
    name, tags = "Mustang", []
    for words, label, tag in MODELS:
        if _has(text, words):
            name, tags = label, [tag]
            break
    for words, tag in GENERATIONS:
        if _has(text, words):
            tags.append(tag)
            break
    return name, tags


def hashtags(post: dict, account: str) -> list[str]:
    _, specific = detect(post)
    fill = ["mustanggt", "mustangnation", "musclecar"]
    tags = ["fordmustang", "mustang"] + specific
    for t in fill:
        if len(tags) >= MAX_HASHTAGS - 1:
            break
        tags.append(t)
    tags = list(dict.fromkeys(tags))[: MAX_HASHTAGS - 1] + [account]
    return tags[:MAX_HASHTAGS]


CREDIT_RX = re.compile(r"(?:credit|credits|video credit|owner|📸|🎥|📹|filmed by|video by|shot by|via|dm)\W{0,6}@([A-Za-z0-9_.]{2,30})",
                       re.IGNORECASE)


def original_creators(post: dict) -> list[str]:
    """Si el post diu de qui és el vídeo (Credit: @x, 📸: @x…), el crèdit també ha d'anar per a aquesta persona."""
    author = (post.get("ownerUsername") or post.get("author") or "").lower()
    found = []
    for h in CREDIT_RX.findall(post.get("caption") or ""):
        h = h.rstrip(".")
        if h.lower() != author and h.lower() not in [f.lower() for f in found]:
            found.append(h)
    return found[:2]


def build(post: dict, style: str, account: str) -> str:
    car, _ = detect(post)
    seed = int(hashlib.md5((post.get("shortCode") or "").encode()).hexdigest(), 16)
    hook = HOOKS[style][seed % len(HOOKS[style])].format(car=car)
    credit = "🎥" if post.get("videoUrl") or post.get("media_type") == "REELS" else "📷"
    author = post.get("ownerUsername") or post.get("author")
    originals = original_creators(post)
    credit_line = (" ".join("@" + o for o in originals) + f" (via @{author})") if originals else f"@{author}"
    tags = " ".join("#" + t for t in hashtags(post, account))
    return (
        f"{hook}\n-\n{FOLLOW[style].format(account=account)}\n-\n"
        f"{credit} by: {credit_line}\n{DISCLAIMER}\n{tags}"
    )
