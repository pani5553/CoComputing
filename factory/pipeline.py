"""
El pipeline: orden escalonado en que trabajan los roles (la "cadena de mando").

Cada agente recibe el trabajo acumulado de los anteriores y deja el suyo para los
siguientes. El orden refleja el SDLC de una empresa real:

  vision -> stack -> requisitos -> diseno -> arquitectura
         -> base de datos -> backend -> frontend
         -> QA -> revision -> seguridad
         -> empaquetado -> documentacion

Nota: database/backend/frontend son conceptualmente paralelos (trabajan sobre el
mismo plano del arquitecto), pero se ejecutan en serie y en este orden porque
backend depende del schema y frontend depende de los endpoints del backend.
"""

PIPELINE: list[str] = [
    "ceo",
    "cto",
    "product_owner",
    "designer",
    "architect",
    "database_engineer",
    "backend_dev",
    "frontend_dev",
    "qa",
    "reviewer",
    "security",
    "devops",
    "tech_writer",
]
