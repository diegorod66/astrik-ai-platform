"""
Herramientas reales del Skills Agent.

Capacidades:
- search_github: buscar herramientas en GitHub
- evaluate_tool: evaluar compatibilidad con el stack
- install_tool: instalar y configurar
- test_tool: probar funcionamiento
- document_tool: documentar instalación
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills"
SKILLS_DIR.mkdir(exist_ok=True)


def search_github(query: str, max_results: int = 10) -> list[dict]:
    """Buscar herramientas en GitHub por query."""
    import requests

    url = "https://api.github.com/search/repositories"
    headers = {"Accept": "application/vnd.github.v3+json"}
    params = {"q": query, "per_page": max_results, "sort": "stars"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("items", []):
            results.append({
                "name": item["full_name"],
                "description": item["description"] or "",
                "url": item["html_url"],
                "stars": item["stargazers_count"],
                "language": item["language"] or "",
                "license": item["license"]["spdx_id"] if item.get("license") else "N/A",
                "topics": item.get("topics", []),
                "updated_at": item["updated_at"],
            })
        return results
    except requests.RequestException as e:
        return [{"error": f"Error buscando en GitHub: {e}"}]


def evaluate_tool(tool: dict) -> dict:
    """Evaluar si una herramienta es compatible con el stack del proyecto.

    Criterios: Python, licencia abierta, comunidad activa, documentada.
    """
    score = 0
    reasons = []

    name = tool.get("name", "")
    desc = (tool.get("description") or "").lower()
    topics = [t.lower() for t in tool.get("topics", [])]
    lang = (tool.get("language") or "").lower()
    stars = tool.get("stars", 0)
    lic = (tool.get("license") or "").upper()

    # Lenguaje
    if lang == "python" or "python" in topics:
        score += 3
        reasons.append("Lenguaje: Python")
    elif lang in ("javascript", "typescript", "rust", "go"):
        score += 2
        reasons.append(f"Lenguaje: {lang}")

    # Licencia
    if lic in ("MIT", "APACHE-2.0", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "GPL-3.0", "LGPL-3.0"):
        score += 2
        reasons.append(f"Licencia: {lic} (open source)")
    else:
        reasons.append(f"Licencia: {lic} (verificar)")

    # Popularidad
    if stars >= 10000:
        score += 3
        reasons.append("Muy popular (>10k stars)")
    elif stars >= 1000:
        score += 2
        reasons.append("Popular (>1k stars)")
    elif stars >= 100:
        score += 1
        reasons.append("Conocida (>100 stars)")

    # Keywords relevantes
    relevant_keywords = ["documentation", "docs", "version", "cli", "python", "git", "markdown"]
    for kw in relevant_keywords:
        if kw in desc or kw in topics:
            score += 1
            reasons.append(f"Keyword relevante: {kw}")

    verdict = "recomendada" if score >= 6 else "posible" if score >= 3 else "no recomendada"

    return {
        "name": name,
        "score": score,
        "verdict": verdict,
        "reasons": reasons,
        "url": tool.get("url", ""),
    }


def install_tool(name: str, install_type: str = "pip", source: str = "") -> dict:
    """Instalar una herramienta.

    Tipos: pip, npm, git, binary, system.
    """
    result = {"tool": name, "type": install_type, "status": "installing", "path": "", "logs": []}

    try:
        if install_type == "pip":
            pkg = source or name
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                capture_output=True, text=True, timeout=120
            )
            result["logs"] = proc.stdout.splitlines()[-5:]
            if proc.returncode == 0:
                result["status"] = "installed"
                result["path"] = _get_pip_path(name)
            else:
                result["status"] = "failed"
                result["logs"].append(proc.stderr)

        elif install_type == "npm":
            proc = subprocess.run(
                ["npm", "install", "-g", name],
                capture_output=True, text=True, timeout=120
            )
            result["logs"] = proc.stdout.splitlines()[-5:]
            result["status"] = "installed" if proc.returncode == 0 else "failed"

        elif install_type == "git":
            dest = SKILLS_DIR / name
            if dest.exists():
                result["status"] = "already_exists"
                result["path"] = str(dest)
            else:
                proc = subprocess.run(
                    ["git", "clone", source or f"https://github.com/{name}.git", str(dest)],
                    capture_output=True, text=True, timeout=120
                )
                result["logs"] = proc.stdout.splitlines()[-5:]
                if proc.returncode == 0:
                    result["status"] = "installed"
                    result["path"] = str(dest)
                else:
                    result["status"] = "failed"
                    result["logs"].append(proc.stderr)

        else:
            result["status"] = "unsupported"
            result["logs"] = [f"Tipo de instalacion no soportado: {install_type}"]

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["logs"] = ["Instalacion agotó el tiempo de espera (120s)"]
    except Exception as e:
        result["status"] = "error"
        result["logs"] = [str(e)]

    return result


def test_tool(name: str, test_command: str = "") -> dict:
    """Probar que una herramienta funciona."""
    cmd = test_command or f"{name} --help"
    try:
        proc = subprocess.run(
            cmd.split(),
            capture_output=True, text=True, timeout=30
        )
        return {
            "tool": name,
            "status": "working" if proc.returncode == 0 else "failing",
            "command": cmd,
            "returncode": proc.returncode,
            "output": (proc.stdout or proc.stderr)[:500],
        }
    except FileNotFoundError:
        return {"tool": name, "status": "not_found", "command": cmd}
    except Exception as e:
        return {"tool": name, "status": "error", "error": str(e)}


def document_tool(name: str, eval_result: dict, install_result: dict,
                  test_result: dict) -> Path:
    """Generar documentación de la herramienta instalada."""
    doc = SKILLS_DIR / name / "SKILL.md"
    content = f"""# Skill: {name}

## Instalacion
- **Fecha:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
- **Tipo:** {install_result.get("type", "N/A")}
- **Estado:** {install_result.get("status", "N/A")}
- **Ruta:** {install_result.get("path", "N/A")}

## Evaluacion
- **Score:** {eval_result.get("score", "N/A")}/10
- **Veredicto:** {eval_result.get("verdict", "N/A")}
- **URL:** {eval_result.get("url", "N/A")}

## Prueba
- **Estado:** {test_result.get("status", "N/A")}
- **Comando:** {test_result.get("command", "N/A")}

## Stack compatible
- Python, Docker, llama.cpp, FastAPI, PostgreSQL, Redis, Qdrant, NATS
"""
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(content, encoding="utf-8")
    return doc


def _get_pip_path(name: str) -> str:
    """Obtener ruta de instalación pip."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "show", name],
            capture_output=True, text=True, timeout=15
        )
        for line in proc.stdout.splitlines():
            if line.lower().startswith("location:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""


def run_full_pipeline(tool_name: str, github_query: str = "",
                      install_type: str = "pip", source: str = "") -> dict:
    """Pipeline completo: buscar -> evaluar -> instalar -> probar -> documentar."""
    query = github_query or tool_name
    results = search_github(query)
    errors = [r for r in results if "error" in r]
    if errors:
        return {"status": "failed", "error": errors[0]["error"]}

    candidates = []
    for r in results[:5]:
        ev = evaluate_tool(r)
        candidates.append({**r, "evaluation": ev})

    if not candidates:
        return {"status": "failed", "error": "No se encontraron herramientas"}

    best = max(candidates, key=lambda c: c["evaluation"]["score"])

    install_res = install_tool(tool_name, install_type, source)
    test_res = test_tool(tool_name)
    doc_path = document_tool(tool_name, best["evaluation"], install_res, test_res)

    return {
        "status": "completed",
        "tool": tool_name,
        "candidates": len(candidates),
        "best_candidate": best["name"],
        "best_score": best["evaluation"]["score"],
        "best_url": best["url"],
        "verdict": best["evaluation"]["verdict"],
        "installation": install_res,
        "test": test_res,
        "documentation": str(doc_path),
    }
