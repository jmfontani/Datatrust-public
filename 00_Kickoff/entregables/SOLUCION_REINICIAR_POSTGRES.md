# Solución: Reinicializar PostgreSQL con pgvector

## Problema
El volumen está en uso porque PostgreSQL sigue corriendo.

## Pasos

### 1. Detener todos los contenedores

```bash
cd <ruta-repo>/00_Kickoff/entregables

docker compose down
```

### 2. Verificar que no quedan contenedores

```bash
docker ps -a
```

**Debe estar vacío o sin `pfm_postgres` ni `pfm_pgadmin`.**

### 3. Eliminar volumen

```bash
docker volume rm entregables_postgres_data
```

**Ahora sí debería funcionar.**

### 4. Si sigue diciendo que está en uso, forzar:

```bash
# Listar todos los contenedores (incluso parados)
docker ps -a

# Si ves alguno de pfm, eliminarlo
docker rm -f pfm_postgres pfm_pgadmin

# Ahora eliminar volumen
docker volume rm entregables_postgres_data
```

### 5. Iniciar de nuevo

```bash
docker compose up -d
```

### 6. Verificar logs (esperar 30 segundos)

```bash
docker compose logs -f db
```

**Buscar mensaje:**
```
✓ BASE DE DATOS INICIALIZADA CORRECTAMENTE
```

### 7. Refrescar pgAdmin

1. Click derecho en servidor → **Disconnect**
2. Click derecho → **Connect**
3. Expande: `Databases → pfm_datasets → Schemas → public → Tables`

---

## Comando rápido (todo en uno)

```bash
cd <ruta-repo>/00_Kickoff/entregables

docker compose down \
  && docker rm -f pfm_postgres pfm_pgadmin 2>/dev/null \
  && docker volume rm entregables_postgres_data 2>/dev/null || true \
  && docker compose up -d \
  && sleep 5 \
  && docker compose logs -f db
```

---

*Si sigue fallando, copiar el error exacto.*
