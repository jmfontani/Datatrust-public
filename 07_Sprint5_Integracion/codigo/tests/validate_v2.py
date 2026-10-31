#!/usr/bin/env python3
"""
Script de validación para Backend V2 + Frontend V2.
Verifica que todo esté correctamente configurado antes de lanzar.
"""
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Verifica versión de Python."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ requerido")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """Verifica dependencias instaladas."""
    required = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'psycopg2': 'psycopg2',
        'streamlit': 'Streamlit',
        'requests': 'Requests',
        'numpy': 'NumPy',
    }
    
    print("\n📦 Verificando dependencias...")
    all_ok = True
    for module, name in required.items():
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name} - instalar con: pip install {module}")
            all_ok = False
    
    return all_ok


def check_postgresql():
    """Verifica conexión a PostgreSQL."""
    print("\n🗄️  Verificando PostgreSQL...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='buscador',
            user='postgres',
            password='postgres'
        )
        cur = conn.cursor()
        
        # Verificar extensión pgvector
        cur.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        has_vector = cur.fetchone()[0]
        
        # Contar datasets
        cur.execute("SELECT COUNT(*) FROM datasets")
        count = cur.fetchone()[0]
        
        print(f"   ✅ PostgreSQL conectado")
        print(f"   ✅ pgvector instalado: {has_vector}")
        print(f"   ✅ Datasets: {count:,}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def check_files():
    """Verifica que existan los archivos necesarios."""
    print("\n📁 Verificando archivos...")
    
    # Detectar directorio base desde la ubicación del script
    script_path = Path(__file__).resolve()
    base = script_path.parent
    
    required_files = [
        base / "api" / "main_v2.py",
        base / "api" / "launch_backend_v2.sh",
        base / "frontend_v2" / "app.py",
        base / "frontend_v2" / "components_v2.py",
        base / "frontend_v2" / "utils_v2.py",
        base / "frontend_v2" / "launch_frontend_v2.sh",
        base / "launch_all_v2.sh",
        base / "stop_backend_frontend_v2.sh",
    ]
    
    all_ok = True
    for file in required_files:
        if file.exists():
            print(f"   ✅ {file.name}")
        else:
            print(f"   ❌ {file.name} - NO ENCONTRADO")
            all_ok = False
    
    return all_ok


def check_ports():
    """Verifica puertos disponibles."""
    print("\n🔌 Verificando puertos...")
    import socket
    
    ports = [8000, 8501]
    all_ok = True
    
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        if result == 0:
            print(f"   ⚠️  Puerto {port} está en uso")
        else:
            print(f"   ✅ Puerto {port} disponible")
        sock.close()
    
    return all_ok


def main():
    print("="*50)
    print("🔍 Validación Backend V2 + Frontend V2")
    print("="*50)
    
    checks = [
        ("Python", check_python_version),
        ("Dependencias", check_dependencies),
        ("PostgreSQL", check_postgresql),
        ("Archivos", check_files),
        ("Puertos", check_ports),
    ]
    
    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
    
    print("\n" + "="*50)
    print("📊 Resumen")
    print("="*50)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
        if not result:
            all_passed = False
    
    print("="*50)
    
    if all_passed:
        print("🎉 Todo listo para lanzar Backend + Frontend V2!")
        print("\nEjecuta:")
        print("  ./launch_all_v2.sh")
        return 0
    else:
        print("⚠️  Hay problemas que deben resolverse antes de lanzar.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
