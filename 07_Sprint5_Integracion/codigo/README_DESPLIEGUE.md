# Buscador Semántico de Datasets - Guía Rápida de Despliegue

## Inicio Rápido (5 minutos)

### 1. Configurar

```bash
cd Datatrust/07_Sprint5_Integracion/codigo
```

Editar `docker/.env`:
```bash
# Windows: notepad docker/.env
# Linux/Mac: nano docker/.env
```

Verificar que contiene:
```env
POSTGRES_PASSWORD=postgres  # Cambiar en producción
API_PORT=8000
STREAMLIT_PORT=8501
```

### 2. Desplegar

```bash
./deploy.sh start
```

Esperar ~30 segundos...

### 3. Verificar

```bash
./deploy.sh test
```

### 4. Usar

- **API**: http://localhost:8000
- **Documentación**: http://localhost:8000/docs
- **Frontend**: http://localhost:8501

---

## Checklist obligatorio antes de desplegar en un servidor

Estos cuatro puntos no vienen resueltos en el repositorio a propósito: dependen del host.

1. **Cambiar la contraseña de PostgreSQL.** El valor por defecto del compose es
   `postgres` y **no debe usarse** fuera de un entorno local. Editar
   `docker/.env` con una contraseña larga y aleatoria (`openssl rand -base64 24`)
   antes del primer `deploy.sh start`, y **no publicar el puerto 5432** al host:
   la API y la base de datos se hablan por la red interna de Docker, así que el
   mapeo `"5432:5432"` del compose sólo es necesario para depurar y conviene
   comentarlo en el despliegue real. Si la base ya se creó con el valor por
   defecto, cambiarla requiere `ALTER USER postgres WITH PASSWORD '...';` (o
   recrear el volumen, lo que destruye los datos).
2. **Dominio y certificado propios.** No hay ningún dominio escrito en el
   repositorio: el frontend se sirve por el puerto 8501 y es responsabilidad del
   despliegue ponerle delante un proxy (nginx/Caddy/Traefik) con su nombre de
   host real y su certificado. El proxy debe:
   - escuchar sólo en 443 para el nombre de host del buscador,
   - **redirigir el 80 a 443**: si el puerto 80 del host ya lo ocupa otro
     servicio (panel de administración, NAS…), una petición al dominio por HTTP
     acabará mostrando ese panel. Declarar un `server` por defecto que devuelva
     444 o redirija evita que el vhost por defecto sea otro servicio;
   - pasar `Upgrade`/`Connection` y desactivar el buffering (Streamlit usa
     websocket), como en el ejemplo de proxy del apartado siguiente.
3. **Cabeceras y versión del servidor.** Añadir `Strict-Transport-Security`,
   `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`,
   `Referrer-Policy: no-referrer` y una CSP básica, y poner `server_tokens off;`
   en nginx para no anunciar su versión. (El servidor actual responde con la
   versión del proxy en la cabecera `Server`.)
4. **Registro DNS.** El dominio del despliegue no se versiona. Si la publicación
   debe ser accesible desde internet, el registro A debe apuntar a la IP pública
   (o a un túnel); si sólo debe verse desde la red local, es preferible no
   publicar un registro con una dirección privada.

> Las contraseñas de ejemplo que aparecen en la documentación de los sprints
> (`LANZAR_CONTENEDOR.md`, `DESPLIEGUE.md`) son ilustrativas y no deben
> reutilizarse en ningún despliegue.

---

## Comandos Principales

| Comando | Descripción |
|---------|-------------|
| `./deploy.sh start` | Iniciar servicios |
| `./deploy.sh stop` | Detener servicios |
| `./deploy.sh restart` | Reiniciar |
| `./deploy.sh status` | Ver estado |
| `./deploy.sh test` | Probar funcionalidad |
| `./deploy.sh logs` | Ver logs |

---

## Verificar que la Mejora Funciona

Test crítico - la palabra "paro" debe devolver empleo, no transporte:

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "paro", "top_k": 5}'
```

**Resultado correcto** (primeros resultados):
- ✅ "Variación relativa del paro registrado"
- ✅ "Porcentaje de paro registrado"
- ✅ "Paro registrado en oficinas de empleo"

**Resultado incorrecto** (si falla la mejora):
- ❌ "Paradas de guaguas"
- ❌ "Paradas de Taxi"

---

## Solución de Problemas Comunes

### Puerto ocupado
```bash
# Cambiar puerto en docker/.env
API_PORT=8001
./deploy.sh restart
```

### No hay resultados
```bash
# La base de datos está vacía - cargar datos
# Ver documentación completa: docs/DESPLIEGUE.md
```

### Docker no responde
```bash
# Verificar Docker está corriendo
docker ps

# Si no, reiniciar Docker Desktop o:
sudo systemctl start docker
```

---

## Documentación Completa

Para detalles avanzados: [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md)

Incluye:
- Instalación manual (sin Docker)
- Configuración de HTTPS
- Backup/Restore
- Monitoreo
- Solución de problemas detallada

---

**Versión**: 2.2.0 | **Última actualización**: 2026-05-25

## Uso de LLM: qué necesita un despliegue

Dos piezas hablan con un modelo de lenguaje y **ninguna es imprescindible** para que el buscador
responda:

| Pieza | Para qué | Variables |
|---|---|---|
| `08_Sprint6_LLM_Mejora/codigo/api/` | expansión de la consulta, re-ranking y validación de metadatos | `OLLAMA_URL`, `LLM_DEFAULT_MODEL`, `LLM_TIMEOUT` |
| `09_Sprint7_RAGAS/codigo/*.py` | juicio de relevancia con LLM para construir el ground truth y calcular las métricas RAGAS | `OLLAMA_API_KEY`, `OLLAMA_URL` |

La clave **no se versiona**. Los scripts la buscan, en este orden, en la variable de entorno
`OLLAMA_API_KEY` y en un `.env` situado en el directorio desde el que se lanza el script o junto a
él:

```bash
export OLLAMA_API_KEY='...'                     # opción 1
printf 'OLLAMA_API_KEY=%s\n' "$CLAVE" > .env     # opción 2 (chmod 600 .env)
```

Comportamiento sin LLM: la API de búsqueda sigue sirviendo resultados con el **fallback léxico**
(ver `08_Sprint6_LLM_Mejora/docs/ARQUITECTURA_FALLBACK_LEXICO.md`); los scripts de evaluación se
detienen con un mensaje explícito, porque sin juez no hay métricas. Fijar `LLM_DEFAULT_MODEL` y
`OLLAMA_URL` deja las cifras comparables entre ejecuciones.

Qué se envía al modelo: consultas de usuario y metadatos públicos de `datos.gob.es`. No se envían
datos personales ni credenciales.
