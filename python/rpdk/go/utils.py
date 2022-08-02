from pathlib import Path

from rpdk.core.exceptions import WizardValidationError

# https://golang.org/ref/spec#Keywords
LANGUAGE_KEYWORDS = {
    "break",
    "default",
    "func",
    "interface",
    "select",
    "case",
    "defer",
    "go",
    "map",
    "struct",
    "chan",
    "else",
    "goto",
    "package",
    "switch",
    "const",
    "fallthrough",
    "if",
    "range",
    "type",
    "continue",
    "for",
    "import",
    "return",
    "var",
}


def safe_reserved(string):
    return f"{string}_" if string in LANGUAGE_KEYWORDS else string


def validate_path(default):
    def _validate_namespace(value):
        if not value:
            return default

        namespace = value

        return namespace

    return _validate_namespace
