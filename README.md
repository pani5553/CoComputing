# 🏭 Agent Factory

Una **software house de agentes IA**. Le das un encargo (brief) y un equipo de
agentes con roles de empresa —CEO, CTO, Product Owner, Arquitecto, Backend Dev,
Frontend Dev, QA…— construye la aplicación completa de principio a fin, de forma
**autónoma**.

No es un chatbot que escribe código suelto: es un **organigrama** donde cada
agente hace **solo su trabajo**, dentro de **su carpeta**, y pasa el testigo al
siguiente en una cadena clara, como en una empresa real.

---

## 🔀 Dos vías para correr el equipo

Hay **dos formas** de usar Agent Factory, según cómo quieras pagar el cómputo:

| Vía | Carpeta | Paga con | Cuándo usarla |
|-----|---------|----------|---------------|
| **A. Motor Python** | `factory/` + `run.py` | **API key** (pago por uso) | Producto/freelance, autonomía total, vendible |
| **B. Subagentes en Claude Code** | `.claude/` | **Tu suscripción Pro/Max** | Desarrollar sin coste extra de API |

- **Vía A** → sigue leyendo este README.
- **Vía B** (recomendada si tienes Pro) → **[COMO-USAR-CLAUDE-CODE.md](COMO-USAR-CLAUDE-CODE.md)** + lanzas `/construir-app` dentro de Claude Code.

Las dos comparten el mismo organigrama, los mismos scopes y el mismo candado por
carpeta (en la vía A es el FileGate de Python; en la B, un hook `scope-guard.ps1`).

---

## Por qué es diferente

| | Un solo LLM "hazme una app" | Agent Factory |
|---|---|---|
| Roles | uno hace todo | 13 especialistas |
| Scope | ilimitado | **cada agente atado a su carpeta (FileGate técnico)** |
| Flujo | improvisado | pipeline escalonado con handoffs |
| Trazabilidad | ninguna | `project_state.json`: artefactos, handoffs, tokens, coste |
| Calidad | variable | revisión + auditoría de seguridad + QA como fases propias |

**La clave:** el scope no es una sugerencia del prompt. El `FileGate` **rechaza
técnicamente** cualquier escritura fuera del área del agente. El Backend Dev
físicamente no puede tocar `frontend/`. Eso es lo que pediste: *que cada uno solo
pueda hacer el trabajo que se le ha asignado*.

---

## El organigrama

```
DIRECCIÓN      🎩 CEO ──────────► 🧠 CTO
                  │ visión           │ stack + arquitectura macro
                  ▼                  ▼
PRODUCTO       📋 Product Owner ─► 🎨 UX/UI Designer
                  │ backlog          │ wireframes + design tokens
                  ▼                  ▼
DISEÑO         🏗️ Software Architect
                  │ estructura + contratos de API + modelo de datos
       ┌──────────┼──────────┐
       ▼          ▼          ▼
CONSTRUCCIÓN  🗄️ DB Eng → ⚙️ Backend Dev → 💻 Frontend Dev
                  │ migrations  │ backend/      │ frontend/
                  ▼
CALIDAD        🧪 QA ──► 🔍 Code Reviewer ──► 🔐 Security Auditor
                  │ tests/   │ docs/05-review   │ docs/06-security
                  ▼
OPERACIONES    🚀 DevOps ──► 📖 Technical Writer
                  │ Docker/CI   │ README + manual + entrega
                  ▼
              ENTREGA ✅
```

Cada rol y su scope exacto: `python run.py --list-roles`.

---

## Instalación

```bash
cd agent-factory
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

copy .env.example .env            # Windows  (cp en Linux/Mac)
# edita .env y pon tu ANTHROPIC_API_KEY
```

API key: https://console.anthropic.com/

---

## Uso

### 1. Probar el flujo SIN gastar API (recomendado la primera vez)
```bash
python run.py --brief briefs/co-computing.md --dry-run
```
Genera la estructura completa con ficheros placeholder. Sirve para ver el
pipeline, comprobar que el scope funciona y revisar el `project_state.json` sin
gastar un céntimo.

### 2. Construir de verdad
```bash
python run.py --brief briefs/co-computing.md
```
El equipo construye la app en `workspace/`. Verás el progreso agente a agente,
con coste por paso.

### 3. Otras opciones
```bash
python run.py --list-roles                              # ver organigrama
python run.py --brief briefs/co-computing.md --only ceo,cto,architect
```

---

## Resultado

Todo se genera en `workspace/`:
```
workspace/
├── docs/            # visión, stack, backlog, diseño, arquitectura, review, seguridad
├── migrations/      # schema SQL  (Database Engineer)
├── backend/         # FastAPI     (Backend Dev)
├── frontend/        # React       (Frontend Dev)
├── tests/           # pruebas     (QA)
├── Dockerfile, docker-compose.yml, .github/   (DevOps)
├── README.md        # documentación final (Technical Writer)
└── project_state.json   # trazabilidad completa del proceso
```

---

## Tu primer encargo: Co-Computing

`briefs/co-computing.md` contiene el encargo del marketplace de cómputo
distribuido (FastAPI + React + Supabase). Es el caso que el equipo construirá.
Para encargar **otra** app, escribe otro brief en `briefs/` y apunta `--brief` a
él. El sistema es genérico.

---

## Arquitectura interna

```
factory/
├── config.py        Settings desde .env
├── filegate.py      Imposición de scope por carpeta (el "candado")
├── state.py         ProjectState: blackboard + handoffs + uso
├── tools.py         read_file, list_dir, write_file, run_command, finish
├── llm.py           Cliente Anthropic: tool-use loop + caching + dry-run
├── agent.py         Agent: ejecuta un rol con su scope y tools
├── roles.py         Los 13 RoleSpec (el organigrama, con prompts y scopes)
├── pipeline.py      Orden escalonado de ejecución
└── orchestrator.py  Corre el pipeline completo end-to-end
run.py               CLI
briefs/              Encargos
workspace/           Donde el equipo construye (generado)
```

### Decisiones de diseño
- **Claude Agent SDK directo** (anthropic-py), no CrewAI/MetaGPT: control total,
  prompt caching, sin magia de framework.
- **Roles como datos** (`roles.py`), no una clase por rol: todo el organigrama se
  lee y se ajusta en un sitio.
- **Workers/devs sin solape**: el scope está diseñado para que cada carpeta tenga
  un único dueño. Backend, frontend y DB nunca chocan.
- **Modelo por tier**: los roles de dirección/arquitectura usan un modelo más
  capaz (`FACTORY_MODEL_DIRECTOR`); el resto, el de por defecto.

---

## Seguridad / coste
- `run_command` solo lo tienen QA y DevOps, y se ejecuta dentro de `workspace/`
  con timeout. Aun así, son comandos generados por un LLM: revísalo antes de
  correrlo en datos sensibles.
- Coste estimado de construir Co-Computing entero: orientativo **$1–4** según
  iteraciones (con caching de prompts). Usa `--dry-run` para validar gratis.

---

## Roadmap
- [ ] Ejecución en paralelo real de Backend/Frontend/DB (async)
- [ ] Bucle de corrección: Reviewer/QA devuelven el trabajo a los devs hasta
      que pase (hoy es un único pase lineal)
- [ ] Checkpoints opcionales de aprobación humana entre fases
- [ ] Métricas de calidad del resultado (cobertura de tests, linters)
