"""
LLMClient — cliente Anthropic con bucle de tool-use, prompt caching y dry-run.

run() ejecuta: system+user -> Claude responde -> si pide tools, las ejecuta via
ToolExecutor y vuelve a llamar -> repite hasta que el agente llama finish() o se
agotan las iteraciones.

dry_run=True NO llama al API: sintetiza una ejecucion (escribe un artefacto de
ejemplo en el scope del rol y llama finish). Sirve para verificar el pipeline,
el FileGate y el estado sin gastar tokens.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .state import Usage
from .tools import ToolExecutor, FinishSignal

# Precios por 1M tokens (USD), por familia de modelo: (input, output, cache_write, cache_read).
# Aproximados — verifica en https://www.anthropic.com/pricing si cambian.
_PRICES = {
    "opus":   (15.0, 75.0, 18.75, 1.50),
    "sonnet": (3.0, 15.0, 3.75, 0.30),
    "haiku":  (1.0, 5.0, 1.25, 0.10),
}


def _price_for(model: str) -> tuple[float, float, float, float]:
    m = (model or "").lower()
    if "opus" in m:
        return _PRICES["opus"]
    if "haiku" in m:
        return _PRICES["haiku"]
    return _PRICES["sonnet"]


@dataclass
class RunResult:
    text: str
    artifacts: list[str]
    finished: Optional[FinishSignal]
    usage: Usage
    iterations: int
    stopped_reason: str = "finished"


class LLMClient:
    def __init__(self, settings):
        self.settings = settings
        self._client = None
        if not settings.dry_run:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=settings.anthropic_api_key)

    def run(
        self,
        *,
        system: str,
        user: str,
        tools: list[dict],
        executor: ToolExecutor,
        model: str,
        max_iterations: int,
        dry_artifact: Optional[tuple[str, str]] = None,
    ) -> RunResult:
        if self.settings.dry_run:
            return self._dry(executor, dry_artifact)
        return self._real(system, user, tools, executor, model, max_iterations)

    # ── Ejecucion real ────────────────────────────────────────────────────────
    def _real(self, system, user, tools, executor, model, max_iterations) -> RunResult:
        messages = [{"role": "user", "content": user}]
        usage = Usage()
        final_text = ""
        stop = "max_iterations"

        for i in range(max_iterations):
            resp = self._client.messages.create(
                model=model,
                max_tokens=8192,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                tools=tools,
                messages=messages,
            )
            u = resp.usage
            usage.add(Usage(
                tokens_in=u.input_tokens, tokens_out=u.output_tokens,
                cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
                cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0,
            ))

            assistant_content = []
            tool_uses = []
            for block in resp.content:
                if block.type == "text":
                    final_text = block.text
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use", "id": block.id,
                        "name": block.name, "input": block.input,
                    })
                    tool_uses.append((block.id, block.name, dict(block.input)))
            messages.append({"role": "assistant", "content": assistant_content})

            if resp.stop_reason != "tool_use":
                stop = "end_turn"
                break

            tool_results = []
            for tid, tname, targs in tool_uses:
                output = executor.execute(tname, targs)
                tool_results.append({
                    "type": "tool_result", "tool_use_id": tid, "content": output,
                })
            messages.append({"role": "user", "content": tool_results})

            if executor.finished:
                stop = "finished"
                break

        p_in, p_out, p_cw, p_cr = _price_for(model)
        usage.cost_usd = round(
            usage.tokens_in / 1e6 * p_in + usage.tokens_out / 1e6 * p_out
            + usage.cache_read / 1e6 * p_cr + usage.cache_write / 1e6 * p_cw, 6,
        )
        return RunResult(
            text=final_text, artifacts=list(executor.artifacts),
            finished=executor.finished, usage=usage,
            iterations=i + 1, stopped_reason=stop,
        )

    # ── Dry-run (sin API) ─────────────────────────────────────────────────────
    def _dry(self, executor: ToolExecutor, dry_artifact) -> RunResult:
        if dry_artifact:
            path, content = dry_artifact
            executor.execute("write_file", {"path": path, "content": content})
        executor.execute("finish", {
            "summary": "[dry-run] artefacto de ejemplo generado sin llamar al API.",
            "handoff": "[dry-run] continua con el siguiente rol del pipeline.",
        })
        return RunResult(
            text="[dry-run]", artifacts=list(executor.artifacts),
            finished=executor.finished, usage=Usage(),
            iterations=1, stopped_reason="dry_run",
        )
