#!/usr/bin/env python
"""
CLI de la Agent Factory.

Ejemplos:
    # Probar el flujo completo SIN gastar API (genera estructura de ejemplo):
    python run.py --brief briefs/co-computing.md --dry-run

    # Construir de verdad (requiere ANTHROPIC_API_KEY en .env):
    python run.py --brief briefs/co-computing.md

    # Correr solo algunos roles:
    python run.py --brief briefs/co-computing.md --only ceo,cto,product_owner

    # Listar el organigrama:
    python run.py --list-roles
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# La consola de Windows suele ser cp1252 y revienta con emojis/acentos.
# Forzamos UTF-8 en la salida para que los logs del organigrama se vean bien.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from factory.config import Settings
from factory.orchestrator import Orchestrator
from factory.pipeline import PIPELINE
from factory.roles import ROLES


def cmd_list_roles():
    print("\nORGANIGRAMA (orden del pipeline):\n")
    for i, rid in enumerate(PIPELINE, 1):
        s = ROLES[rid]
        scope = ", ".join(s.allowed_write) or "(solo lectura)"
        flags = []
        if s.can_run:
            flags.append("ejecuta")
        if s.director:
            flags.append("director")
        tag = f" [{', '.join(flags)}]" if flags else ""
        print(f" {i:>2}. {s.emoji}  {s.title:<22} {s.level:<13} scope: {scope}{tag}")
    print()


def main():
    p = argparse.ArgumentParser(description="Agent Factory — equipo de agentes que construye apps")
    p.add_argument("--brief", help="Ruta al fichero del encargo (markdown)")
    p.add_argument("--dry-run", action="store_true", help="Prueba el flujo sin llamar al API")
    p.add_argument("--only", default="", help="IDs de roles separados por coma (subconjunto del pipeline)")
    p.add_argument("--list-roles", action="store_true", help="Muestra el organigrama y sale")
    args = p.parse_args()

    if args.list_roles:
        cmd_list_roles()
        return

    if not args.brief:
        p.error("falta --brief (o usa --list-roles)")

    brief_path = Path(args.brief)
    if not brief_path.exists():
        sys.exit(f"[ERROR] no existe el brief: {brief_path}")
    brief = brief_path.read_text(encoding="utf-8")

    settings = Settings.load(dry_run=args.dry_run)
    settings.require_key()

    only = [r.strip() for r in args.only.split(",") if r.strip()] or None
    if only:
        unknown = [r for r in only if r not in ROLES]
        if unknown:
            sys.exit(f"[ERROR] roles desconocidos: {unknown}. Validos: {list(ROLES)}")

    Orchestrator(settings).run(brief, only=only)


if __name__ == "__main__":
    main()
