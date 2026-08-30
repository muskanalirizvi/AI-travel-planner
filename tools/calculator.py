"""Safe arithmetic evaluator exposed as a LangGraph/LangChain tool."""

import ast
import operator

from langchain_core.tools import tool

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError(f"unsupported constant: {node.value!r}")

    if isinstance(node, ast.BinOp):
        op = _BINARY_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"unsupported operator: {type(node.op).__name__}")
        return op(_eval_node(node.left), _eval_node(node.right))

    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"unsupported operator: {type(node.op).__name__}")
        return op(_eval_node(node.operand))

    raise ValueError(f"unsupported expression: {ast.dump(node)}")


def safe_eval(expression: str) -> float:
    """Parse and evaluate a numeric expression using only a whitelisted AST grammar.

    Supports +, -, *, /, //, %, ** with parentheses and unary +/-. No names,
    calls, attributes, subscripts, or comparisons are permitted, so this never
    executes arbitrary code the way eval() would.
    """
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid expression: {expression!r}") from exc
    return _eval_node(parsed.body)


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic math expression and return the numeric result.

    Use this for arithmetic such as budget totals, splitting costs among
    travelers, unit conversions, or tallying trip expenses, e.g.
    "250*3 + 80", "(1200 + 340) / 4", "5000 * 0.012". Supports +, -, *, /,
    //, %, ** and parentheses. Does not support variables or functions.
    """
    try:
        result = safe_eval(expression)
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        return f"Error evaluating expression '{expression}': {exc}"

    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return str(result)
