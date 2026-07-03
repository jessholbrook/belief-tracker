import math

import pytest

from app.agent import _safe_eval, execute_custom_tool


def test_basic_arithmetic():
    assert _safe_eval("2 * (3 + 4)") == "14"
    assert _safe_eval("7 // 2") == "3"
    assert _safe_eval("-3 % 5") == "2"
    assert _safe_eval("2 ** 10") == "1024"


def test_math_module_access():
    assert _safe_eval("math.sqrt(2)") == str(math.sqrt(2))
    assert _safe_eval("sqrt(16)") == "4.0"
    assert _safe_eval("math.pi") == str(math.pi)
    assert _safe_eval("pi") == str(math.pi)


@pytest.mark.parametrize(
    "expression",
    [
        # Classic empty-__builtins__ sandbox escapes.
        "().__class__.__bases__[0].__subclasses__()",
        "__import__('os').system('echo pwned')",
        "open('/etc/passwd').read()",
        "getattr(math, 'sqrt')",
        "[x for x in (1,)]",
        "'a' * 10",  # strings are not numbers
        "math.__loader__",
        "lambda: 1",
    ],
)
def test_rejects_non_arithmetic(expression):
    with pytest.raises((ValueError, SyntaxError)):
        _safe_eval(expression)


def test_rejects_huge_exponents():
    with pytest.raises(ValueError, match="Exponent too large"):
        _safe_eval("9 ** 9 ** 9")


def test_rejects_keyword_arguments():
    with pytest.raises(ValueError, match="Keyword arguments"):
        _safe_eval("math.pow(2, exp=3)")


def test_execute_custom_tool_wraps_errors():
    output, is_error = execute_custom_tool(
        "calculate", {"expression": "__import__('os')"}
    )
    assert is_error
    assert "Tool error" in output

    output, is_error = execute_custom_tool("calculate", {"expression": "1 + 1"})
    assert not is_error
    assert output == "2"


def test_unknown_tool():
    output, is_error = execute_custom_tool("nope", {})
    assert is_error
