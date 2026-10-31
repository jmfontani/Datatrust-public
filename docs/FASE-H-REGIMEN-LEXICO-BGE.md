# Fase H · Re-verificación con BGE del hallazgo de la Fase C

**Fecha:** 30-sep-2026
**Resultado:** **el hallazgo de la Fase C NO se mantiene con BGE.**
Script `154_regimen_lexico_bge.py` · Entregable `fase_h_REGIMEN_LEXICO.json`.

---

## Qué decía la Fase C (con MiniLM, instrumento viejo)

> El motor ganador depende del régimen del solapamiento de vocabulario: si la
> consulta copia el vocabulario del catálogo, gana el **léxico** (0,7331 vs
> 0,5468); si no lo copia, semántico y léxico empatan (0,35) y gana el
> **híbrido** (0,4223). **El híbrido es el único que no pierde en ningún régimen.**

Esa tesis era, hasta hoy, el argumento para conservar el peso léxico del híbrido.

## Cómo se re-verifica

- **Misma lógica:** tercios de solapamiento consulta-catalogo (tokens de la
  consulta presentes en título+descripción del top-10), sobre las mismas 214
  consultas y el mismo GT v5 con el instrumento canónico.
- **Motor:** BGE-M3 en producción (`/search`, los tres repartos de pesos).

## Resultado

### nDCG@10 por régimen (BGE-M3)

| régimen | n | híbrido 0,7/0,3 | semántico 1,0/0,0 | léxico 0,0/1,0 | solap. medio |
|---|---|---|---|---|---|
| bajo | 71 | 0,3825 | **0,3954** | 0,1412 | 0,47 |
| medio | 71 | 0,6468 | **0,6626** | 0,4508 | 0,93 |
| alto | 72 | 0,6421 | **0,6426** | 0,3851 | 1,00 |

### Comparación pareada léxico − semántico

| régimen | diff | IC95 | veredicto |
|---|---|---|---|
| bajo | **−0,2542** | [−0,3435 · −0,1650] | semántico mejor |
| medio | **−0,2118** | [−0,2966 · −0,1271] | semántico mejor |
| alto | **−0,2574** | [−0,3385 · −0,1764] | semántico mejor |

## Lectura

1. **Con BGE, el régimen que hacía ganar al léxico desaparece.** Ni siquiera con
   solapamiento del 100 % el canal léxico se acerca (0,3851 vs 0,6426): el semántico
   con BGE captura el vocabulario copiado **y además el resto**.
2. **El léxico en solitario queda peor de lo que se sabía** (0,14-0,45): con BGE
   disponible, el canal léxico no defiende ningún régimen.
3. **El híbrido ya no es el que «no pierde en ningún régimen»**: pierde frente al
   semántico (ligeramente) en bajo y medio, empata en alto.
4. **La comparación pareada es la que manda** (elimina la varianza entre consultas):
   −0,21 a −0,26 en los tres tercios, **todas con intervalo lejos de cero**. No es
   ruido: es un desplome del canal léxico.

## Consecuencia para los pesos del híbrido

Se mantiene 0,7/0,3 (empate global con 1,0/0,0 en `fase_h_PESOS.json`, −0,0175
también cruce del 0,3/0,7), pero **cambia el argumento**:

> Antes defendía el 0,3 léxico: «el híbrido no pierde en ningún régimen».
> **Ya no vale.** Con BGE el léxico no gana ningún régimen.
> El fundamento honesto del 0,3/0,7 es ahora doble: (a) **empate global** con el
> semántico puro, y (b) red de seguridad para consultas con vocabulario muy
> específico (nombres propios, variantes ortográficas) que **no** quedan
> representadas en el GT actual. Es una prudencia defendible, no un dato medido.

**Para la memoria del TFM:** la historia de la Fase C sigue siendo válida como
hallazgo *sobre el motor MiniLM* — motivó la migración y detectó la contaminación.
Pero el argumento del híbrido debe contarse con los datos de BGE; citar el
«no pierde en ningún régimen» como razón actual del 0,3 sería incorrecto.

## Caveats

- El régimen se mide con un proxy (presencia de tokens), como en la Fase C; el
  resultado es solido porque la comparación es pareada dentro de cada tercio.
- El léxico con `weights 0,0/1,0` usa la misma expansión de sinónimos y el mismo
  `ts_rank` normalizado del resto de sistemas, de modo que la comparación aísla el
  canal.
- La muestra del régimen «bajo» (71 consultas con solapamiento medio 0,47) tiene
  nDCG bajos en general: son consultas donde el GT tiene poco nivel 2.