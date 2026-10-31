# Fase H · Pesos del híbrido con BGE-M3

**Fecha:** 30-sep-2026
**Pregunta:** tras adoptar BGE-M3, ¿qué reparto de pesos conviene entre canal
semántico y canal léxico?
**Estado:** medido. **Decisión pendiente de confirmar por el interesado.**

## Motivación

Con MiniLM el canal léxico aportaba de forma clara: quitar el peso léxico
(1,0/0,0) **empeoraba** el nDCG en **+0,0537 a favor del híbrido** (significativo,
IC95 [0,0339 · 0,0736], `fase_f_HIBRIDO_MINILM.json`). La Fase F midió con BGE el
par 0,7/0,3 frente a 1,0/0,0 y la diferencia se desvaneció: **−0,0072**, IC95
[−0,0227 · 0,0083], no significativa.

El reparto **invertido (semántico 0,3 / léxico 0,7) nunca se había medido**. El
único dato de BGE con peso distinto de 0,7/0,3 era 1,0/0,0.

## Qué se mide

Script `150_pesos_hibrido_bge.py`. Las **mismas 214 consultas**, el **mismo
instrumento canónico** (`utils/gt_metrics.py`) y el **mismo GT v5** (10.653
etiquetas) que las Fases E/F/G. Motor: **BGE-M3 en producción** (`embedding_bge`,
vía `/search`).

Tres repartos, escritos en la convención del proyecto **(semántico/léxico)**:

| pesos (sem/léx) | nDCG@10 | IC95 | P@5 | MRR | cobertura |
|---|---|---|---|---|---|
| **0,7 / 0,3** (actual) | **0,5575** | [0,5113 · 0,6038] | 0,4224 | 0,5895 | 92,6 % |
| **1,0 / 0,0** (solo semántico) | **0,5672** | [0,5206 · 0,6138] | 0,4383 | 0,5997 | 93,4 % |
| **0,3 / 0,7** (invertido) | **0,5400** | [0,4942 · 0,5858] | 0,4084 | 0,5843 | 93,6 % |

## Comparación pareada contra el actual

| cambio | diff | IC95 | veredicto |
|---|---|---|---|
| semántico (1,0/0,0) | **+0,0097** | [−0,0055 · +0,0249] | **empate** (cruza cero) |
| invertido (0,3/0,7) | **−0,0175** | [−0,0357 · +0,0006] | **empate** (cruza cero) |

**Ninguno de los dos cambios es distinguible del actual.** El orden de las medias
favorece a 1,0/0,0, pero el intervalo cruza cero; el margen es del orden de la
mejora mínima detectable.

Entregable: `entregables/fase_h_PESOS.json`.

## Lectura

1. **Con BGE, el reparto de pesos deja de importar.** MiniLM era sensible al canal
   léxico (+0,0537 significativo); BGE no. Lo mismo que ya se vio al medir el
   híbrido frente al semántico puro, y coherente con que BGE recupere mejor el
   vocabulario por sí solo.
2. **El canal léxico no aporta, pero tampoco estorba.** El invertido cae 0,0175
   (tendencia a peor, no conclusión). El léxico **en solitario** sigue siendo malo
   en ambos motores (nDCG 0,3269, cobertura 0,6822): no resuelve por sí mismo.
3. **Argumento para no quitarlo:** en la Fase C quedó establecido que el híbrido es
   *el único que no pierde en ningún régimen* — cuando la consulta copia el
   vocabulario del catálogo, el léxico gana. Ese hallazgo se midió con otro
   instrumento y otra base de consultas; **no se ha re-verificado con BGE**.
4. **Caveat de instrumento:** la medición del par 0,7/0,3 frente a 1,0/0,0 de la
   Fase F es del **29-sep por la mañana**, **antes** del arreglo de determinismo.
   Esta medición de la Fase H es **posterior** al arreglo. La de esta fase es la
   válida.

## Dónde viven los pesos (tres sitios, y no coinciden)

| sitio | valores | quién lo usa |
|---|---|---|
| `main_v2_final_v07.py:583-584` | **0,7 / 0,3** | `/search` **solo si no se envían pesos** |
| `routes_v10.py:94-95` | **0,75 / 0,25** | `/llm/search/fast` |
| `/app/public/app.py:79-80` (UI pública) | **0,75 / 0,25** | **la interfaz que ve el usuario** — envía los pesos explícitos a `/search` |

**Consecuencia importante:** cambiar los valores por defecto de la API **no cambia
nada en lo que el usuario ve por la web**, porque la UI pública envía 0,75/0,25
explícitos en cada petición. Los defaults de `main_v2_final_v07.py` solo afectan a
llamadas directas a la API sin pesos (por ejemplo, los scripts de medición). Para
mover la experiencia de la web hay que tocar `/app/public/app.py`.

El modo avanzado (`?mode=advanced`) sí expone deslizadores al usuario
(`legacy/components_v2.py:292`, 0,7/0,3 por defecto).

## Pendiente de decisión

- ¿Qué reparto se fija como predeterminado, y en **cuál de los tres sitios**?
- ¿Se re-verifica con BGE el hallazgo de la Fase C de que el híbrido no pierde en
  ningún régimen? Es lo que sostiene el argumento para conservar el canal léxico.
