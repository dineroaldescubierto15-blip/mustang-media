# mustang-media

Repositori de suport per a l'automatització de @mustangemotion.

## Estructura

- `config/sources.json` — hashtags i creadors que es vigilen cada dia.
- `data/history.json` — posts ja publicats (per no repetir fotos ni autors).
- `images/` — imatges aprovades, amb URL pública perquè l'API d'Instagram les pugui llegir.

## Flux

1. Cerca diària de candidats (hashtags + creadors de `config/sources.json`).
2. Puntuació de viralitat i filtre amb `data/history.json`.
3. Els millors candidats s'envien per Telegram per aprovar-los (✅ / ❌).
4. Make publica els aprovats a les 12:00 i les 19:00 (America/New_York), sempre amb crèdit a l'autor.
