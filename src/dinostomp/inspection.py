"""What does this pod's Python actually touch?

`--trust-code` asks you to accept running a stranger's code. Asking for that
without showing you the code is asking for blind consent, and "read it
yourself" is advice people skip. This reads it for you: it parses each pod-local
Python file and reports, statically, what capabilities it reaches for.

Being clear about what this is NOT:

  - it is NOT a sandbox. Nothing here prevents anything. It informs a decision
    that only you can make.
  - it is NOT a malware detector. A determined author can obfuscate any of
    this, and a clean report is not a safety certificate.
  - the capabilities it flags are not automatically bad. A legitimate scorer may
    open a data file. A judge may call an API. The point is that you should know
    BEFORE you run it, not be surprised afterwards.

Static parsing only: this never imports the file, which is the entire point.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

# Modules whose presence changes what a file can do to your machine. Grouped by
# what a reader would actually want to be told.
CAPABILITY_MODULES = {
    "runs other programs": {"subprocess", "os", "pty", "multiprocessing", "signal"},
    "talks to the network": {"socket", "urllib", "http", "requests", "httpx", "ftplib",
                             "smtplib", "telnetlib", "asyncio", "aiohttp"},
    "writes or deletes files": {"shutil", "tempfile", "pathlib", "io", "sqlite3", "zipfile",
                                "tarfile", "pickle", "shelve", "dbm"},
    "loads code dynamically": {"importlib", "imp", "ctypes", "cffi", "marshal", "types"},
    "reads the environment": {"getpass", "platform", "sysconfig"},
}

# Builtins that turn data into code, or reach outside the process.
DANGEROUS_CALLS = {
    "eval": "evaluates a string as code",
    "exec": "executes a string as code",
    "compile": "compiles a string into code",
    "__import__": "imports a module chosen at runtime",
    "open": "opens a file",
    "input": "blocks waiting for stdin",
    "breakpoint": "drops into a debugger",
}

# Attribute calls worth naming even when the module import looks innocuous.
DANGEROUS_ATTRS = {
    "system": "os.system runs a shell command",
    "popen": "opens a subprocess",
    "run": "subprocess.run executes a program",
    "call": "subprocess.call executes a program",
    "check_output": "subprocess.check_output executes a program",
    "remove": "deletes a file",
    "unlink": "deletes a file",
    "rmtree": "deletes a directory tree",
    "urlopen": "makes a network request",
}

# `x.loads(...)` is only alarming for deserialisers that can execute code.
# json.loads cannot, and flagging it would teach readers to ignore the report,
# which is worse than saying nothing.
UNSAFE_DESERIALISERS = {"pickle", "marshal", "shelve", "dill", "cPickle"}


@dataclass
class Finding:
    line: int
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"line {self.line}: {self.detail}"


@dataclass
class FileReport:
    path: str
    findings: list[Finding] = field(default_factory=list)
    imports: set[str] = field(default_factory=set)
    error: str = ""
    top_level_effects: int = 0

    @property
    def clean(self) -> bool:
        return not self.findings and not self.error


def _dotted(node: ast.AST) -> str:
    """`urllib.request` from the AST, so a finding names what it actually saw
    rather than a bare `?`."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts)) or "?"


def _root_module(name: str) -> str:
    return (name or "").split(".")[0]


def inspect_source(source: str, path: str = "<pod>") -> FileReport:
    """Parse one file and report what it reaches for. Never imports it."""
    report = FileReport(path=path)
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        report.error = f"will not parse: {exc}"
        return report

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                report.imports.add(_root_module(alias.name))
        elif isinstance(node, ast.ImportFrom):
            report.imports.add(_root_module(node.module or ""))
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in DANGEROUS_CALLS:
                report.findings.append(
                    Finding(node.lineno, "call", f"calls {func.id}(): {DANGEROUS_CALLS[func.id]}"))
            elif isinstance(func, ast.Attribute):
                owner = _dotted(func.value)
                if func.attr == "loads":
                    if owner.split(".")[0] in UNSAFE_DESERIALISERS:
                        report.findings.append(Finding(
                            node.lineno, "call",
                            f"calls {owner}.loads(): deserialises, which can execute code"))
                elif func.attr in DANGEROUS_ATTRS:
                    report.findings.append(Finding(
                        node.lineno, "call",
                        f"calls {owner}.{func.attr}(): {DANGEROUS_ATTRS[func.attr]}"))

    for group, modules in CAPABILITY_MODULES.items():
        hit = sorted(report.imports & modules)
        if hit:
            report.findings.append(Finding(0, "import", f"{group}: imports {', '.join(hit)}"))

    # Statements at module level run at IMPORT time, which is before any check
    # gets a chance to look at anything. That is the sharp end.
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef, ast.Assign,
                                 ast.AnnAssign, ast.Expr, ast.Pass)):
            report.top_level_effects += 1
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            report.top_level_effects += 1
    if report.top_level_effects:
        report.findings.append(Finding(
            0, "import-time",
            f"{report.top_level_effects} statement(s) run at IMPORT time, before any check sees "
            "them"))
    return report


def inspect_file(path: Path) -> FileReport:
    try:
        source = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        rep = FileReport(path=str(path))
        rep.error = f"cannot read: {exc}"
        return rep
    return inspect_source(source, str(path))
