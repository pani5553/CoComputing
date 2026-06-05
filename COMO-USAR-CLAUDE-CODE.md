# 🏢 Equipo de agentes en Claude Code (vía suscripción Pro)

Esta es la **segunda vía** de Agent Factory: en lugar del motor Python (que usa API
key de pago), aquí el equipo de 13 agentes vive **dentro de Claude Code** y corre
con tu **suscripción Claude Pro** — sin coste extra de API.

## Qué hay montado

```
.claude/
├── agents/                      # los 13 subagentes (un rol cada uno)
│   ├── factory-ceo.md
│   ├── factory-cto.md
│   ├── factory-product-owner.md
│   ├── factory-designer.md
│   ├── factory-architect.md
│   ├── factory-database-engineer.md
│   ├── factory-backend-dev.md
│   ├── factory-frontend-dev.md
│   ├── factory-qa.md
│   ├── factory-reviewer.md
│   ├── factory-security.md
│   ├── factory-devops.md
│   └── factory-tech-writer.md
├── skills/
│   └── construir-app/SKILL.md   # el orquestador: /construir-app
└── scripts/
    └── scope-guard.ps1          # el "candado": impone el scope de cada agente
```

## El candado de scope (lo que pediste)

Cada subagente tiene un **hook `PreToolUse`** que, antes de cada escritura, ejecuta
`scope-guard.ps1` y comprueba que el fichero cae dentro de **su** carpeta. Si el
Backend Dev intenta tocar `frontend/`, se le **bloquea** y se le devuelve el error
para que se corrija. No es solo el prompt: es un candado técnico, igual que el
FileGate del motor Python.

| Rol | Solo puede escribir en |
|-----|------------------------|
| CEO | `docs/00-vision.md` |
| CTO | `docs/01-stack.md` |
| Product Owner | `docs/02-requisitos.md`, `docs/02-backlog.md` |
| Designer | `docs/03-design/**` |
| Architect | `docs/04-*.md` |
| Database Engineer | `migrations/**` |
| Backend Dev | `backend/**` |
| Frontend Dev | `frontend/**` |
| QA | `tests/**` |
| Reviewer | `docs/05-review.md` |
| Security | `docs/06-security.md` |
| DevOps | `Dockerfile`, `docker-compose.yml`, `.github/**`, `deploy/**` |
| Tech Writer | `README.md`, `docs/07-*.md` |

## Cómo usarlo

1. **Abre Claude Code en esta carpeta** (`agent-factory/`):
   ```
   cd C:\Users\ogarc\OneDrive\Escritorio\clase\agent-factory
   claude
   ```
   (o abre la carpeta en VS Code con la extensión de Claude Code).

2. **Reinicia/abre la sesión** para que cargue los subagentes nuevos. Compruébalo:
   ```
   /agents
   ```
   Deberías ver los 13 `factory-*` en la lista.

3. **Activa el modo autónomo** para que no te pregunte por cada fichero: pulsa
   **Shift+Tab** hasta ver *"accept edits"* (auto-acepta ediciones). El candado de
   scope sigue protegiendo cada carpeta aunque actives esto.

4. **Lanza la construcción**:
   ```
   /construir-app briefs/co-computing.md
   ```
   La sesión principal irá delegando en los 13 subagentes por orden, y construirá la
   app en esta carpeta (`backend/`, `frontend/`, `migrations/`, `docs/`, `tests/`, ...).

## Sobre los límites de Pro

Construir la app entera son muchos pasos. Con **Pro** puedes toparte con el límite
de uso por horas a media construcción. Por eso el orquestador trabaja por **bloques**
(producto/diseño → construcción → calidad/entrega). Si la sesión se corta:
- espera al reset del límite,
- vuelve a abrir Claude Code aquí,
- lanza `/construir-app` y dile *"continúa desde donde se quedó"* (mirará qué
  carpetas ya existen y seguirá).

## Permisos (por qué no toqué tu settings.json)

Para que sea 100% autónomo haría falta auto-aceptar escrituras. **No** te lo
configuré yo en `settings.json` a propósito: auto-otorgarse permisos es algo que
debes decidir tú. Tienes dos opciones:
- **Por sesión (recomendado):** Shift+Tab → *accept edits* (paso 3 de arriba).
- **Permanente:** crea tú `.claude/settings.json` con
  `{"permissions": {"allow": ["Write", "Edit"]}}` si quieres que no pregunte nunca.

## Las dos vías, comparadas

| | Motor Python (`factory/`) | Subagentes Claude Code (`.claude/`) |
|---|---|---|
| Paga con | API key (de pago) | Tu suscripción Pro |
| Candado de scope | FileGate (Python) | hook scope-guard.ps1 |
| Autonomía | Total (`python run.py`) | Alta (orquestada por la sesión) |
| Límites | Solo tu crédito | Límite de uso de Pro |
| Ideal para | Producto/vender a cliente | Tú, sin coste extra |
