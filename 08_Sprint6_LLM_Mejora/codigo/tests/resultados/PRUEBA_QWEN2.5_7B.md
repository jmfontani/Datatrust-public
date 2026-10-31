# Prueba Comparativa: Qwen2.5:7b vs DeepSeek-v4-Flash

**Fecha:** 2026-05-31  
**Propósito:** Comparar rendimiento del modelo local qwen2.5:7b vs cloud deepseek-v4-flash:cloud

---

## ⚠️ Resultado de la Prueba

**El modelo qwen2.5:7b NO funcionó correctamente** en el pipeline de re-ranking.

### Problemas Detectados

| Métrica | DeepSeek (Cloud) | Qwen2.5:7b (Local) | Estado |
|---------|------------------|---------------------|--------|
| **Tiempo respuesta** | ~30-60s | ~120s (timeout) | ❌ Qwen más lento |
| **Score generado** | 6.0-10.0 | 0.0 (fallo) | ❌ Qwen no genera scores |
| **Explicaciones** | ✅ Completas | ❌ Vacías | ❌ Qwen no responde JSON |
| **Formato JSON** | ✅ Válido | ❌ Timeout/Error | ❌ Fallo parseo |

### Observaciones

1. **Timeout**: El modelo qwen2.5:7b tardó exactamente 120s (timeout configurado) en cada query
2. **Respuesta vacía**: El modelo respondió pero el formato no fue el JSON esperado
3. **Score 0.0**: Fallback por fallo en el parseo de la respuesta

### Posibles Causas

1. **Velocidad**: qwen2.5:7b en CPU es significativamente más lento que deepseek en cloud
2. **Formato JSON**: El prompt puede ser incompatible con qwen (diferente estructura de respuesta)
3. **Temperatura/Parámetros**: Los parámetros optimizados para deepseek pueden no funcionar con qwen

---

## Archivos Generados

```
resultados/
├── bateria_qwen_2026-05-31_222047_para_evaluar.csv   # Fallo (scores 0.0)
└── PRUEBA_QWEN2.5_7B.md                               # Este informe
```

## Archivos para Pruebas Futuras

```
motor/
├── llm_reranker.py                                    # Original (deepseek)
├── llm_reranker_qwen.py                               # Versión qwen (copia)
└── llm_reranker_backup_deepseek.py                  # Backup original
```

---

## Recomendación

**NO usar qwen2.5:7b para re-ranking** hasta que:
1. Se pruebe con GPU (actualmente corre en CPU)
2. Se ajuste el prompt específicamente para qwen
3. Se aumente el timeout a 300s o más
4. Se verifique compatibilidad de formato JSON

**DeepSeek-v4-flash:cloud sigue siendo la mejor opción** para producción.

---

## Configuración para Futuras Pruebas

Para intentar de nuevo con qwen2.5:7b:

```python
# En llm_client.py, cambiar preset:
PRESETS = {
    "reranking": {
        "model": "qwen2.5:7b",
        "temperature": 0.1,
        "num_predict": 4000,
        "top_p": 0.9,
        "timeout": 300  # Aumentar a 300s
    }
}
```

O usar el archivo:
```bash
# Backup del actual
cp llm_reranker.py llm_reranker_deepseek.py

# Copia versión qwen
cp llm_reranker_qwen.py llm_reranker.py

# Reiniciar API
pkill -f main_v2_final_v07.py
python3 main_v2_final_v07.py
```

---

**Conclusión**: La prueba fue infructuosa. Qwen2.5:7b no es viable actualmente sin optimización adicional del prompt y hardware (GPU).
