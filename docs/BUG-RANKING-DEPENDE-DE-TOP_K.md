# Bug del motor: el ranking depende de `top_k`

**Fecha:** 24-sep-2026
**Descubierto:** durante el cierre de la Fase B, al investigar por qué la
cobertura del top-10 no llegaba al 100 %.
**Gravedad:** alta. Afecta a toda medición y a la comparabilidad entre
experimentos. No afecta a la corrección del ground truth.

---

## 1. El síntoma

Se construyó el pool de juicio con **top-20** y se evaluó con **top-10**. La
intersección debería ser total (el top-10 de un ranking es un prefijo del top-20
del mismo ranking). No lo era.

Comprobación directa, con la consulta `consumo agua embalses`:

| top_k | primer resultado |
|---|---|
| 5 | `266fb371-718` |
| 10 | `572dfff3-bae` |
| 20 | `db65f397-7ef` |
| 30 | `48b236ef-e73` |

**Cuatro primeros resultados distintos para la misma consulta.** Un motor de
recuperación nunca debería cambiar su orden según cuántos resultados se pidan.

---

## 2. Alcance medido

Sobre las 47 consultas del GT, con la configuración 0,7/0,3:

| efecto | consultas |
|---|---|
| el **primer** resultado cambia al cambiar `top_k` | **9/47 (19 %)** |
| el **top-5** cambia al cambiar `top_k` | **21/47 (45 %)** |
| el top-5 **no está contenido** en el top-10 | 1/47 |

Y la cobertura de la Fase B se quedó en **98 %** en lugar del 100 % esperado:
**10 fichas del top-10 evaluado no estaban en el pool de su propia consulta**,
porque el pool se construyó con un ranking que ya no era el mismo.

---

## 3. La causa

En `08_Sprint6_LLM_Mejora/codigo/api/main_v2_final_v07.py`:

```python
# ambos motores recuperan un multiplo del top_k pedido
LIMIT %s   ...  request.top_k * 3          # semantico (linea 741)
LIMIT %s   ...  request.top_k * 3          # lexico    (linea 843)

# y despues normalizan por el MAXIMO DEL CONJUNTO RECUPERADO
max_rank = max(float(r['rank']) for r in rows)     # linea 847
r['rank'] = float(r['rank']) / max_rank            # linea 850

max_lex_score = max(r["score"] for r in lexical_results)   # linea 789
r["score"] = r["score"] / max_lex_score                    # linea 792
```

El normalizador **no es una constante**: es el máximo de lo que haya entrado en
el corte. Al cambiar `top_k` cambia el corte, cambia el máximo y cambian **todos**
los scores. El orden se reorganiza.

### 3.1 Dos problemas superpuestos

1. **Normalización dependiente del corte.** `r / max(conjunto)` hace que el
   ranking dependa de cuántos documentos se recuperen. Es la causa directa de que
   cambie el orden.

2. **El máximo no es un normalizador válido.** `ts_rank_cd` devuelve valores sin
   cota superior, y dividir por el máximo local fuerza que **el primer resultado
   valga siempre 1,0**. Se descarta la magnitud absoluta de la coincidencia: una
   consulta con coincidencias excelentes y otra con coincidencias mediocres
   producen el mismo score máximo.

Se ve en los datos: con `top_k=5` la consulta `empleo_001` da 0,5033; con
`top_k=10`, 0,7019. No es que el resultado sea mejor: es que el máximo del corte
es distinto.

---

## 4. Qué consecuencias tiene

### 4.1 Sobre las métricas ya medidas

**Todas las cifras de las Fases A y B están medidas con `top_k=10`.** Son válidas
**para `top_k=10`** y no se pueden extrapolar a 5 o a 20. Hay que declararlo.

La comparación entre sistemas sigue siendo justa: los tres se midieron con el
mismo `top_k`. Pero el valor absoluto depende del corte elegido.

### 4.2 Sobre la comparabilidad (lo grave)

Si el ranking depende de `top_k`, y el pool se construye con uno y se evalúa con
otro, **se juzgaron documentos que la configuración evaluada no devuelve**, y al
revés. Eso rompe la premisa de que cobertura del pool y evaluación hablan del
mismo conjunto.

### 4.3 Sobre el ground truth (no afecta)

El GT **no** está afectado. Su unidad es `(consulta, dataset_id)`, no una
posición: la etiqueta de una ficha no depende de dónde aparezca. El
desacoplamiento que se buscaba en `GT-EMBEDDINGS-DESACOPLAMIENTO.md` resulta
todavía más valioso de lo previsto, porque protege el GT de este bug.

### 4.4 Sobre la migración a BGE-M3

Refuerza la decisión de no migrar todavía: comparar dos encoders cuyos rankings
dependen del corte daría diferencias que no son del encoder.

---

## 5. Cómo arreglarlo

**Opción A · No normalizar por el máximo (recomendada).**
Fusionar con los scores en su escala natural:

```
score_final = sem_w * similitud_coseno + lex_w * ts_rank_normalizado_por_constante
```

La similitud coseno ya está en [0,1] (los embeddings se generan con
`normalize_embeddings=True`). Para `ts_rank_cd` hay que usar una **constante**
—no el máximo del corte— o un `rank/(rank+k)` (saturación monótona), que tampoco
depende del conjunto.

**Opción B · Normalización global precalculada.**
Calcular los máximos una vez sobre el catálogo completo y guardarlos. Es estable
pero añade un paso de mantenimiento: hay que recalcularlos al reindexar.

**Opción C · Recuperar siempre un número fijo.**
Recuperar N fijo (p. ej. 1000) y recortar la respuesta a `top_k` al final. El
corte deja de depender de `top_k`, así que el orden se establece. Es el cambio
más pequeño y preserva el comportamiento actual, pero mantiene el problema 2
(el máximo local sigue borrando la magnitud).

**Recomendación:** **A**, con la prueba de que el ranking es invariante a `top_k`
como criterio de aceptación.

### 5.1 Verificación del arreglo

Un test que debe pasar después:

```
para cada consulta y para k en {5,10,20,30}:
    ranking(k)[:5] == ranking(30)[:5]
```

Hoy falla en **21 de 47 consultas (45 %)**. Ese número es la línea base del
arreglo.

---

## 6. Por qué importa para el fin del TFM

El fin es **decidir con datos si un motor es mejor que otro**. Con este bug:

- dos motores pueden diferir sólo porque sus cortes internos difieren;
- una mejora real puede quedar enmascarada por un reordenamiento espurio;
- las cifras no son reproducibles si alguien pide `top_k` distinto.

**Arreglarlo es requisito para que las Fases D-F signifiquen algo.** Va antes que
la migración a BGE-M3.

---

## 7. Estado

- **Diagnóstico:** cerrado, con causa localizada en el código y efecto medido.
- **Arreglo:** **no aplicado.** Cambia el comportamiento del motor de producción;
  requiere decisión explícita.
- **Test de aceptación:** definido (§5.1), con su línea base (falla en 21/47).
