# Estudi de reels virals del nínxol Mustang (novembre 2026)

Base de criteris per a la cerca i selecció de reels de @mustangemotion. Implementat a
`scripts/viral_score.py` (puntuació) i aplicat a la cerca diària i al banc de reels.

## Mostra i mètode
- 379 reels recollits de 56 hashtags del nínxol (Apify), filtrats: només família Mustang, sense IA,
  motos, anuncis ni publicitat. 322 vàlids per a l'anàlisi (amb visualitzacions i ≥7 dies d'antiguitat).
- Mediana: 210.000 visualitzacions · 25% superen 1M · 42% superen 300.000.
- Per cada reel: plans (talls de càmera), durada, ritme, brillantor, color, moviment, volum, so original o
  música, text en pantalla (OCR) i text del post. Revisió visual de fulls de fotogrames dels millors i pitjors.
- Comparacions per medianes i taxes d'èxit (% >300k i >1M), perquè les visualitzacions tenen una
  distribució molt desigual.

## Resultats (mediana de visualitzacions)
| Senyal | Amb | Sense | Efecte |
|---|---|---|---|
| Mustang clàssic (1964-1973, fastback, Eleanor, Mach 1) | 426k | 184k | ×2,3 |
| Imatge fosca / nocturna (brillantor < 45) | 685k | 192k | ×3,6 · 72% > 300k |
| So original (motor, escapament) vs música | 269k | 219k | ×1,2 · 48% vs 40% > 300k |
| Muntatge lleuger (4-8 plans) | 318k | 1 pla 193k · 2-3 plans 133k · 9+ plans 95k | millor ritme |
| Text en pantalla al primer segon | 231k | 201k | ×1,15 |
| Text original amb pregunta (enganxa-comentaris) | 67k | 228k | ×0,3 |
| Drift / burnout | 29k | — | molt per sota |
| Durada | sense efecte clar (de 6 a 60+ s funcionen) | | |

## Què funciona (patrons visuals)
1. **Nostàlgia i icones**: Eleanor, fastbacks 67-69, Mach 1, restauracions (transformació, procés).
2. **Ambient**: cotxe negre de nit amb llums, posta de sol, pla estètic quiet.
3. **POV amb so**: conduint, canvi manual, interior amb el motor sonant.
4. **Ganxo escrit curt** a la pantalla: opinió o meme ("Your daily reminder why you don't like electric
   cars", "Entering the weekend like…", "This sounds CRAZY").
5. **Humor i jocs de paraules** amb el cavall ("Reasons mustangs are called mustangs").

## Què evitar
- Drift i burnouts genèrics, passejades al voltant d'un cotxe aparcat de dia, exposicions mal il·luminades.
- Muntatges amb molts talls ràpids i música genèrica.
- Contingut fet amb IA, anuncis de venda, publicitat de productes, cotxes que no són Mustang.

## Limitacions
- L'API de hashtags no dona els seguidors de cada autor: no es pot separar del tot l'efecte de la mida del compte.
- Algunes categories tenen mostra petita (nit n=25): s'han de confirmar amb els resultats reals de @mustangemotion.
- Revisar l'estudi cada mes amb les dades dels posts publicats (estil de caption, format, hora).
