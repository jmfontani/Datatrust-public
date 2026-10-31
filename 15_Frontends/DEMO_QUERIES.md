# 📋 Queries Recomendados para Demo en Vivo

**Fecha:** 2026-06-04  
**Propósito:** Lista de queries que funcionan perfecto para demo del TFM

---

## 🎯 Plan de Demo Recomendado (15 minutos)

### **Minuto 0-2: Apertura con Frontend B (Producto)**
**URL:** http://localhost:8502

| Query | Por qué funciona | Qué mostrar |
|-------|-----------------|-------------|
| `despoblación rural` | Muchos resultados, tema actual | Vista limpia, resultados relevantes |
| `empleo juvenil` | Datos EPA, paro, afiliación | Facetas por territorio y tema |
| `calidad del aire` | Medio ambiente, sensores | Filtros por publisher (gobierno) |

---

### **Minuto 2-7: Profundización con Frontend A (Técnico)**
**URL:** http://localhost:8501

| Query | Qué demostrar | Controles a usar |
|-------|---------------|------------------|
| `transporte público Madrid` | Pesos semántico vs léxico | 100% léxico → 100% semántico |
| `violencia género estadísticas` | Facetas + filtros | Filtrar por territorio + tema |
| `precios alquiler vivienda` | Umbral de score | 0.20 → 0.50 → 0.80 |

**Ejemplo de guion:**
> "Como ven, con 100% semántico obtenemos resultados conceptualmente relacionados aunque no usen las mismas palabras exactas. Si bajamos a 100% léxico, solo coinciden los términos exactos..."

---

### **Minuto 7-10: Pico Técnico con Frontend C (LLM)**
**URL:** http://localhost:8503

| Query | Qué demuestra | Nota |
|-------|---------------|------|
| `empleo juvenil` | Re-ranking LLM | Comparar con/sin LLM |
| `despoblación` | Explicaciones de relevancia | Mostrar "¿Por qué es relevante?" |

**Advertencia:** El LLM puede tardar 3-5 segundos (local) o 60-80 segundos (cloud). Tener paciencia en la demo.

---

### **Minuto 10-15: Vuelta a Frontend B + Preguntas**

---

## 🔄 Queries de Respaldo (Backup)

Si alguna query falla o no muestra resultados relevantes:

| Categoría | Query | Resultados esperados |
|-----------|-------|---------------------|
| Demografía | `población mayor 65 años` | Estadísticas por edad |
| Economía | `PIB comunidades autónomas` | Datos económicos regionales |
| Educación | `universidades públicas` | Centros educativos |
| Sanidad | `hospitales centros salud` | Infraestructura sanitaria |
| Cultura | `museos archivos` | Equipamiento cultural |
| Deporte | `instalaciones deportivas` | Polideportivos, piscinas |

---

## ⚠️ Queries a EVITAR en la demo

Estas queries pueden dar resultados pobres o confusos:

| Query | Problema |
|-------|----------|
| `bitcoin` | Pocos resultados específicos |
| `inteligencia artificial` | Demasiado genérico |
| `covid-19` | Datos posiblemente desactualizados |
| `turismo sostenible` | Concepto muy abstracto |
| Queries en inglés | El modelo es multilingüe pero funciona mejor en español |

---

## 🎬 Guión Paso a Paso

### **1. Apertura (Frontend B)**
```
1. Abrir http://localhost:8502
2. Escribir "despoblación rural"
3. Click en "Buscar"
4. Mostrar primeros 3-5 resultados
5. Expandir facetas en sidebar (si está visible)
```

### **2. Demo Técnica (Frontend A)**
```
1. Abrir http://localhost:8501
2. Escribir "transporte público Madrid"
3. Sidebar → mostrar controles de pesos
4. Mover slider: 100% semántico → resultados
5. Mover slider: 100% léxico → otros resultados
6. Explicar diferencia
```

### **3. Demo LLM (Frontend C) - OPCIONAL**
```
1. Abrir http://localhost:8503
2. Escribir "empleo juvenil"
3. Activar "Re-ranking con LLM"
4. Mostrar diferencia en ranking
5. Click en "¿Por qué es relevante?" en 1-2 resultados
```

---

## 📊 Métricas para mencionar durante la demo

| Métrica | Valor | Fuente |
|---------|-------|--------|
| Datasets indexados | **87.676** | `/health` endpoint |
| Tiempo de respuesta | **~30-50 ms** | Frontend (sin LLM) |
| Tiempo con LLM | **~3-5 s** (local) | Frontend C |
| Embeddings | **384 dimensiones** | sentence-transformers |
| Base de datos | **PostgreSQL 15.4 + pgvector** | `/health` |

---

## 🛠️ Checklist Pre-Demo

- [ ] API corriendo en puerto 8000 (`curl http://localhost:8000/health`)
- [ ] Frontend B corriendo en puerto 8502
- [ ] Frontend A corriendo en puerto 8501 (backup)
- [ ] Frontend C corriendo en puerto 8503 (si se usa LLM)
- [ ] Navegador con las 3 pestañas abiertas
- [ ] Queries de respaldo anotadas en un papel
- [ ] Capturas de pantalla guardadas (plan B por si falla la demo)

---

## 📸 Capturas de Seguridad (Plan B)

Si la demo falla, tener preparadas:

1. **Screenshot 1:** Frontend B con query "despoblación" y resultados
2. **Screenshot 2:** Frontend A con controles de pesos visibles
3. **Screenshot 3:** Frontend C con explicación LLM expandida

**Comando para capturar desde terminal:**
```bash
# Si tienes scrot instalado
scrot -d 3 demo_frontend_b.png
```

---

*Documento creado para Sprint 11 - Evaluación del Buscador Semántico*
