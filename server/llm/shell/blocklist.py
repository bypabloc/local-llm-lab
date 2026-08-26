import re
import shlex

# ponytail: lista plana de (patrón regex, motivo) en vez de una jerarquía de
# reglas — agregar un patrón nuevo es una línea, no requiere tocar lógica.
# Ver .claude/rules/shell-execution.md para el criterio de qué entra acá.
_BLOCKED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\brm\s+.*-[a-z]*r[a-z]*f|\brm\s+.*-[a-z]*f[a-z]*r"),
        "rm recursivo forzado",
    ),
    (
        re.compile(r"\brm\b.*\s(/|~|\$HOME|\.{1,2})(\s|$)"),
        "rm apuntando a raíz/home/directorio actual",
    ),
    (re.compile(r"\bdd\s+if="), "dd puede sobrescribir un disco entero"),
    (re.compile(r"\bmkfs(\.\w+)?\b"), "formateo de filesystem"),
    (re.compile(r"\bfdisk\b|\bparted\b"), "particionado de disco"),
    (re.compile(r">\s*/dev/"), "redirección a un device"),
    (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:&?\s*\}\s*;\s*:"), "fork bomb"),
    (re.compile(r"\bsudo\b|\bsu\b|\bdoas\b"), "escalación de privilegios"),
    (re.compile(r"\bchmod\b.*\b777\b"), "chmod 777"),
    (re.compile(r"\bchown\b.*-R\b"), "chown recursivo"),
    (re.compile(r"\|\s*(sh|bash|zsh)\b"), "pipe de descarga directo a un shell"),
    (re.compile(r"\bnc\b.*-l\b|\bnetcat\b.*-l\b"), "listener de red"),
    (re.compile(r"\bgit\s+push\b.*(--force|-f)\b"), "git push --force"),
    (re.compile(r"\bgit\s+reset\b.*--hard\b"), "git reset --hard"),
    (re.compile(r"\bgit\s+clean\b.*-[a-z]*f"), "git clean forzado"),
    (
        re.compile(r"\bapt\b.*\b(remove|purge)\b"),
        "desinstalación de paquete del sistema",
    ),
    (re.compile(r"\bpip\s+uninstall\b"), "desinstalación de paquete pip"),
    (
        re.compile(r">\s*/etc/|>\s*/boot/|>\s*/sys/"),
        "escritura sobre directorio del sistema",
    ),
    (re.compile(r"\bkill\s+-9\s+1\b"), "kill a PID 1 (init)"),
    (re.compile(r"\bkillall\b"), "killall (mata procesos por nombre, sin filtro)"),
    (re.compile(r"\bpkill\b(?!.*-f\s+\S+)"), "pkill sin -f con patrón específico"),
]


def is_blocked(command: str) -> str | None:
    """Devuelve el motivo si `command` matchea el blocklist, None si es seguro.

    Revisa el comando completo (para patrones que dependen de un separador,
    como un pipe a un shell) y también cada sub-comando de una cadena
    (&&, ;, |) por separado, así un comando peligroso no puede colarse
    escondido detrás de uno inocuo.
    """
    candidates = [command, *_split_chain(command)]
    for candidate in candidates:
        for pattern, reason in _BLOCKED_PATTERNS:
            if pattern.search(candidate):
                return reason
    return None


def _split_chain(command: str) -> list[str]:
    parts = re.split(r"&&|\|\||;|\|", command)
    return [p.strip() for p in parts if p.strip()]


def parse_shell_safe(command: str) -> list[str]:
    """Tokeniza `command` respetando comillas, para subprocess sin shell=True."""
    return shlex.split(command)
