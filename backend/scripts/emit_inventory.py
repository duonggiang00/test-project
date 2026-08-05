import ast
import inspect
import json
import pkgutil
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.routing import APIRoute
from pydantic import BaseModel

import app.models  # noqa: F401
import app.schemas as schemas_package
from app.db.base import Base
from app.main import app


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def type_name(value: Any) -> str:
    if value is None:
        return "None"
    if hasattr(value, "__name__"):
        return value.__name__
    return str(value).replace("typing.", "")


def callable_name(value: Any) -> str:
    module = getattr(value, "__module__", None)
    name = getattr(value, "__qualname__", None) or getattr(value, "__name__", None)
    if name is None:
        module = value.__class__.__module__
        name = value.__class__.__qualname__
    return f"{module}.{name}".strip(".")


def model_inventory() -> list[dict[str, Any]]:
    models = []
    for mapper in sorted(Base.registry.mappers, key=lambda item: item.class_.__name__):
        columns = []
        for column in mapper.columns:
            columns.append(
                {
                    "name": column.name,
                    "type": str(column.type),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "unique": bool(column.unique),
                    "foreign_keys": sorted(
                        foreign_key.target_fullname for foreign_key in column.foreign_keys
                    ),
                }
            )

        relationships = []
        for relationship in mapper.relationships:
            relationships.append(
                {
                    "name": relationship.key,
                    "target": relationship.mapper.class_.__name__,
                    "direction": relationship.direction.name,
                    "uselist": relationship.uselist,
                    "secondary": (
                        relationship.secondary.name if relationship.secondary is not None else None
                    ),
                }
            )

        models.append(
            {
                "class": mapper.class_.__name__,
                "module": mapper.class_.__module__,
                "table": mapper.local_table.name,
                "columns": columns,
                "relationships": sorted(relationships, key=lambda item: item["name"]),
            }
        )
    return models


def schema_inventory() -> list[dict[str, Any]]:
    schemas = []
    module_names = [schemas_package.__name__]
    module_names.extend(
        f"{schemas_package.__name__}.{module.name}"
        for module in pkgutil.iter_modules(schemas_package.__path__)
    )

    for module_name in sorted(module_names):
        module = __import__(module_name, fromlist=["*"])
        for name, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate is BaseModel or not issubclass(candidate, BaseModel):
                continue
            if candidate.__module__ != module.__name__:
                continue
            fields = []
            for field_name, field in candidate.model_fields.items():
                fields.append(
                    {
                        "name": field_name,
                        "type": type_name(field.annotation),
                        "required": field.is_required(),
                    }
                )
            schemas.append(
                {
                    "class": name,
                    "module": module.__name__,
                    "fields": fields,
                }
            )
    return sorted(schemas, key=lambda item: (item["module"], item["class"]))


def dependency_names(route: Any) -> list[str]:
    names: set[str] = set()

    def visit(dependant) -> None:
        for dependency in dependant.dependencies:
            if dependency.call is not None:
                names.add(callable_name(dependency.call))
            visit(dependency)

    visit(route.dependant)
    return sorted(names)


def effective_api_routes(routes: list[Any]):
    """Yield concrete API routes across FastAPI's lazy included-router graph."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
            continue

        candidates = getattr(route, "effective_candidates", None)
        if not callable(candidates):
            continue
        for candidate in candidates():
            if isinstance(getattr(candidate, "original_route", None), APIRoute):
                yield candidate
            else:
                yield from effective_api_routes([candidate])


def route_inventory() -> list[dict[str, Any]]:
    routes = []
    for route in effective_api_routes(app.routes):
        routes.append(
            {
                "path": route.path,
                "methods": sorted(route.methods or []),
                "name": route.name,
                "endpoint": callable_name(route.endpoint),
                "response_model": type_name(route.response_model),
                "dependencies": dependency_names(route),
            }
        )
    return sorted(routes, key=lambda item: (item["path"], item["methods"]))


def decorator_markers(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    markers = []
    for decorator in node.decorator_list:
        try:
            rendered = ast.unparse(decorator)
        except Exception:
            continue
        if "pytest.mark." in rendered:
            markers.append(rendered.split("pytest.mark.", 1)[1].split("(", 1)[0])
    return sorted(set(markers))


def test_inventory() -> list[dict[str, Any]]:
    entries = []
    tests_root = BACKEND_ROOT / "tests"
    for path in sorted(tests_root.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        tests = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                tests.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "markers": decorator_markers(node),
                    }
                )
        relative_path = path.relative_to(BACKEND_ROOT).as_posix()
        entries.append(
            {
                "path": relative_path,
                "tier": "unit" if "unit" in path.parts else "integration",
                "tests": sorted(tests, key=lambda item: (item["line"], item["name"])),
            }
        )
    return entries


def alembic_heads() -> list[str]:
    configuration = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(configuration)
    return sorted(script.get_heads())


def main() -> None:
    payload = {
        "models": model_inventory(),
        "schemas": schema_inventory(),
        "routes": route_inventory(),
        "tests": test_inventory(),
        "alembic_heads": alembic_heads(),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
