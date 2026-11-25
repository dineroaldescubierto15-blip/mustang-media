"""Generació de captions per a @mustangemotion.

Tres estils que roten (per poder comparar després quin funciona millor):
  A · Clàssic: model + pregunta curta de resposta fàcil
  B · Debat: puntuació de l'1 al 10
  C · Comunitat: crida a etiquetar-nos i a compartir
Màxim 5 hashtags (límit d'Instagram des de desembre de 2025).
"""
import hashlib

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
    (["rtr"], "Mustang RTR", "mustangrtr"),
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


def detect(post: dict) -> tuple[str, list[str]]:
    """Retorna el nom del cotxe i els hashtags específics (model, generació)."""
    text = _text(post)
    name, tags = "Mustang", []
    for words, label, tag in MODELS:
        if any(w in text for w in words):
            name, tags = label, [tag]
            break
    for words, tag in GENERATIONS:
        if any(w in text for w in words):
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


def build(post: dict, style: str, account: str) -> str:
    car, _ = detect(post)
    seed = int(hashlib.md5((post.get("shortCode") or "").encode()).hexdigest(), 16)
    hook = HOOKS[style][seed % len(HOOKS[style])].format(car=car)
    credit = "🎥" if post.get("videoUrl") or post.get("media_type") == "REELS" else "📷"
    author = post.get("ownerUsername") or post.get("author")
    tags = " ".join("#" + t for t in hashtags(post, account))
    return (
        f"{hook}\n-\n{FOLLOW[style].format(account=account)}\n-\n"
        f"{credit} by: @{author}\n{DISCLAIMER}\n{tags}"
    )
