# Sistema de Gestión de Biblioteca

API REST para administrar catálogo, socios, préstamos, devoluciones y multas.
Python 3.10+ · FastAPI · pytest.

## Ejecutar
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn library.api:app --reload      # docs en http://127.0.0.1:8000/docs
```

## Pruebas y calidad
```bash
pytest            # incluye cobertura; falla si baja de 95 %
ruff check .      # análisis estático / estilo
```

## Arquitectura (capas)
| Capa | Archivo | Responsabilidad |
|---|---|---|
| Dominio | `domain.py` | Entidades, validaciones y reglas puras. Sin dependencias externas |
| Persistencia | `repositories.py` | Interfaces abstractas + implementación en memoria |
| Aplicación | `services.py` | Casos de uso (`LibraryService`) |
| Presentación | `api.py` | Endpoints HTTP y mapeo de errores a códigos |

Buenas prácticas aplicadas: separación de responsabilidades, inyección de
dependencias (repositorios y reloj), validación en el dominio, excepciones
propias, reloj inyectable para pruebas deterministas, tipado, cobertura mínima
exigida y linter.

## Reglas de negocio
- Préstamo de **14 días**; máximo **3 préstamos activos** por socio.
- No se presta si el socio tiene préstamos **vencidos**, ya tiene ese libro o no hay copias.
- Multa de **$500 COP por día** de retraso al devolver.
- ISBN de 10 o 13 dígitos (guiones permitidos); correo único por socio.

## Endpoints
| Método | Ruta | Descripción | Errores |
|---|---|---|---|
| POST | `/books` | Crear libro | 409 duplicado, 422 inválido |
| GET | `/books?q=` | Buscar por título/autor | |
| POST | `/members` | Registrar socio | 409 correo repetido, 422 |
| POST | `/loans` | Prestar libro | 404, 422 regla de negocio |
| POST | `/loans/{id}/return` | Devolver y calcular multa | 404, 422 |
| GET | `/members/{id}/loans` | Préstamos activos | 404 |

## Estrategia de pruebas
- **Unitarias de dominio** (`test_domain.py`): valores límite (día 14 vs 15), clases de equivalencia (ISBN/correo), parametrización.
- **Servicio** (`test_services.py`): reglas de negocio, atomicidad (el stock no cambia si el préstamo falla).
- **API / integración** (`test_api.py`): flujo completo y códigos HTTP.
