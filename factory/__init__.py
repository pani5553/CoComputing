"""
Agent Factory — una "software house" de agentes IA.

Un equipo de agentes con roles de empresa (CEO, CTO, Product Owner, Arquitecto,
Backend Dev, Frontend Dev, ...) que, dado un encargo (brief), construye una
aplicacion completa de principio a fin de forma autonoma.

Principios de diseno:
  1. SCOPE ESTRICTO: cada agente solo puede escribir en SU carpeta. No es solo
     una instruccion del prompt — lo impone el FileGate tecnicamente.
  2. FLUJO ESCALONADO: los agentes trabajan en cadena (pipeline), cada uno
     recibe el trabajo del anterior via handoff y deja el suyo para el siguiente.
  3. TRAZABILIDAD: cada paso queda registrado en project_state.json (artefactos,
     resumenes, tokens, coste).

Modulos:
  config        Settings desde .env
  filegate      Imposicion de scope por carpeta
  state         ProjectState (blackboard compartido + handoffs)
  tools         Definicion y ejecucion de tools (read/write/list/run/finish)
  llm           Cliente Anthropic con tool-use loop + prompt caching (+ dry-run)
  agent         Clase Agent: ejecuta un rol con su scope y tools
  roles         RoleSpec de los 13 roles (el organigrama)
  pipeline      Orden escalonado de ejecucion
  orchestrator  Corre el pipeline completo end-to-end
"""

__version__ = "0.1.0"
