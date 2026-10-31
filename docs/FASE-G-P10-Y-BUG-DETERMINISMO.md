# Fase G — P@10, y un bug de reproducibilidad que afecta a PRODUCCIÓN

Fecha: 2026-09-29

---

## 1. P@5 y P@10 (lo que se pedía)

Nunca se habían medido a 10: el instrumento canónico usa `k_precision=5`, y P@10 no
es derivable de lo guardado (nDCG y MRR no lo contienen, y los rankings por consulta
no se guardaban). Medido ahora, sobre híbrido 0,7/0,3, GT v5, umbral nivel 2:

| motor | P@5 | P@10 | P@10/P@5 | MRR | nDCG@10 | cob@5 | cob@10 |
|---|---|---|---|---|---|---|---|
| MiniLM (actual) | 0,3458 | 0,2977 | 0,86 | 0,4932 | 0,4249 | 100 % | 100 % |
| **BGE-M3** | **0,4224** | **0,3879** | 0,92 | **0,5895** | **0,5575** | 95,0 % | 92,6 % |

Diferencia pareada: **P@5 +0,0766** [+0,0387 · +0,1146] · **P@10 +0,0902**
[+0,0543 · +0,1261] → **distinguible en ambas**.

Lectura: la ventaja de BGE-M3 **crece** al pasar de 5 a 10 puestos (+0,0766 → +0,0902).
`P@10/P@5` = 0,92 frente a 0,86 significa que BGE-M3 mantiene la densidad de aciertos
al profundizar en la lista; MiniLM se degrada más rápido. El hueco no estaba solo en
acertar el primero, estaba en la cola.

Valor determinista de BGE P@5: **0,4224**. Las cifras anteriores (0,4290 y 0,4215)
eran el mismo sistema medido en dos momentos distintos del bug de la §2.

---

## 2. El hallazgo de fondo: producción es NO DETERMINISTA

Al buscar por qué BGE no reproducía entre ejecuciones, apareció un bug real **en el
código de producción**:

```python
expanded = set(words)          # conjunto de str
...
for w in expanded:             # <-- iteración de un SET
    if w not in result:
        result.append(w)
```

El orden de iteración de un `set` de `str` depende de `PYTHONHASHSEED`, que es
**aleatorio en cada arranque del proceso**. Por tanto el texto expandido con sinónimos
sale en orden distinto en cada reinicio, y como el vector depende del texto, **el
ranking cambia sin que nadie toque nada**.

Está en los dos ficheros: `08_Sprint6_LLM_Mejora/codigo/api/main_v2_final_v07.py`
(líneas 261-276, producción) y el clon de `09_Sprint7_RAGAS`.

**Medición del efecto:** reordenar los sinónimos mueve el vector con coseno
**0,990-0,994 (BGE-M3)** y **0,978-0,992 (MiniLM)** — suficiente para alterar el orden.

**Aislamiento limpio (producción 8000 frente a un clon con el mismo código):**

| consultas | rankings coinciden |
|---|---|
| 12 con sinónimos en la consulta | **solo 6 coinciden** |
| 8 sin sinónimos (control) | **8 de 8 coinciden** |

Es decir: el no-determinismo aparece exactamente en las consultas que activan la
expansión por sinónimos, y en ninguna otra. Control perfecto.

**14 de las 214 consultas** del banco activan la expansión, así que el efecto sobre
las métricas agregadas es pequeño (de ahí que MiniLM pareciera estable: su P@5 salió
0,3458 en las tres mediciones, aunque sus rankings individuales sí cambian). Pero es
un defecto de reproducibilidad de primer orden: dos evaluaciones del mismo sistema
pueden dar rankings distintos, y una auditoría no puede reproducir un resultado.

---

## 3. Arreglo

```python
for w in sorted(expanded):
```

Determinista, sin cambiar la semántica de la expansión (mismo conjunto de términos,
solo orden fijo). Verificado: el texto expandido es idéntico en 3 arranques
consecutivos, y los 11/11 rankings de consultas con sinónimos reproducen exactamente
tras reiniciar el clon.

**NO aplicado a producción**: es un fichero modificado sin commit y el usuario no ha
autorizado el cambio del buscador en servicio. Queda propuesto: es una línea, en
`main_v2_final_v07.py:276`, y haría producción reproducible.

Ojo con el orden de las operaciones: al corregirlo en producción cambiará el texto
expandido (y por tanto los rankings) de esas 14 consultas respecto a lo que hay
ahora. No es solo un arreglo de estilo: conviene medir su efecto antes y después.

---

## 4. Artefactos

- `147_precision_10.py` — P@5/P@10 + caché de rankings (`cache_resultados_faseg.json`)
- `fase_g_PRECISION.json` — resultado de la §1
- `gestionar_clon.sh` — arranque/parada del clon (ojo: en esta imagen NO existe `kill`
  ni `pkill` en el `$PATH`; hay que iterar `/proc` y usar `os.kill` desde Python)
