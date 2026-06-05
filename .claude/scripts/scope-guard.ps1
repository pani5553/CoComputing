# ============================================================
#  scope-guard.ps1  —  El "FileGate" de la vía Claude Code.
#
#  Hook PreToolUse: se ejecuta ANTES de cada Write/Edit de un subagente.
#  Lee el JSON del evento por stdin, saca tool_input.file_path y comprueba
#  que cae dentro del scope permitido para ESE subagente (los patrones se
#  pasan como argumentos). Si está fuera -> exit 2 (bloquea + avisa a Claude).
#
#  Patrones admitidos (igual que el FileGate de Python):
#    "backend/"            carpeta y todo lo que cuelga
#    "docs/05-review.md"   un fichero exacto
#    "docs/03-design/**"   glob recursivo
#
#  Uso en el frontmatter del subagente (exec form, robusto en Windows):
#    hooks:
#      PreToolUse:
#        - matcher: "Write|Edit|MultiEdit"
#          hooks:
#            - type: command
#              command: powershell
#              args: ["-NoProfile","-ExecutionPolicy","Bypass","-File",
#                     "${CLAUDE_PROJECT_DIR}\\.claude\\scripts\\scope-guard.ps1",
#                     "backend/"]
# ============================================================

param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Allowed)

# Si no nos pasan scope, no bloqueamos nada (fail-open en config, no en seguridad).
if (-not $Allowed -or $Allowed.Count -eq 0) { exit 0 }

# Leer el JSON del evento desde stdin.
$raw = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

try { $data = $raw | ConvertFrom-Json } catch { exit 0 }

# Extraer la ruta objetivo.
$fp = $null
if ($data.tool_input) { $fp = $data.tool_input.file_path }
if ([string]::IsNullOrWhiteSpace($fp)) { exit 0 }   # sin path -> nada que validar

# Raíz del proyecto: preferimos el cwd del evento; si falta, el actual.
$root = $data.cwd
if ([string]::IsNullOrWhiteSpace($root)) { $root = (Get-Location).Path }

# Normalizar a rutas absolutas.
try {
    if (-not [System.IO.Path]::IsPathRooted($fp)) { $fp = Join-Path $root $fp }
    $full = [System.IO.Path]::GetFullPath($fp)
    $rootFull = [System.IO.Path]::GetFullPath($root)
} catch { exit 0 }

# ¿Intenta salirse del proyecto? (p. ej. ..\..\algo)
if (-not $full.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    [Console]::Error.WriteLine("BLOQUEADO (scope): '$fp' esta fuera del proyecto. Solo puedes tocar ficheros del proyecto.")
    exit 2
}

# Ruta relativa al proyecto, con / como separador.
$rel = $full.Substring($rootFull.Length).TrimStart('\', '/').Replace('\', '/')

foreach ($pat in $Allowed) {
    $p = $pat.Replace('\', '/')
    if ($p.EndsWith('/**')) {
        $pre = $p.Substring(0, $p.Length - 3)
        if ($rel -eq $pre -or $rel.StartsWith($pre + '/')) { exit 0 }
    }
    elseif ($p.EndsWith('/')) {
        $pre = $p.TrimEnd('/')
        if ($rel -eq $pre -or $rel.StartsWith($pre + '/')) { exit 0 }
    }
    else {
        if ($rel -eq $p -or $rel -like $p) { exit 0 }
    }
}

[Console]::Error.WriteLine("BLOQUEADO (scope): no puedes escribir en '$rel'. Tu scope permitido es: $($Allowed -join ', '). Cinete a tu area de responsabilidad y deja lo demas en el handoff.")
exit 2
