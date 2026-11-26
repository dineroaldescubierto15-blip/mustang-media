"""Filtre de rellevància compartit: família Mustang sí; pickups, Cobra clàssic, IA, motos i anuncis no."""


def make_filter(config: dict):
    keywords = [k.lower() for k in config.get("required_keywords", [])]
    strong = [k.lower() for k in config.get("strong_keywords", [])]
    excluded = [k.lower() for k in config.get("excluded_keywords", [])]
    blocked = [k.lower() for k in config.get("blocked_keywords", [])]

    def is_relevant(post: dict) -> bool:
        text = " ".join([post.get("caption") or "", " ".join(post.get("hashtags") or [])]).lower()
        if keywords and not any(k in text for k in keywords):
            return False
        if any(k in text + " " for k in blocked):
            return False
        if any(k in text for k in excluded) and not any(k in text for k in strong):
            return False
        return True

    return is_relevant
