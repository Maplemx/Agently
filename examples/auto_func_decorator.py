from typing import Any
from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "model_type": "chat",
    },
).set_settings("debug", True)

agent = Agently.create_agent()


@agent.tool_func
async def add(a: int, b: int) -> int:
    """
    Return result of `a(int)` add `b(int)`
    """
    import asyncio

    await asyncio.sleep(1)
    print(a, "+", b, "=", a + b)
    return a + b


@agent.tool_func
async def python_code_executor(
    python_code: str,
):
    """
    Execute Python code and get final result.
    Use print() to throw processing results.
    """
    import io
    import asyncio
    import contextlib

    result_io = io.StringIO()
    local_vars: dict[str, Any] = {}

    try:
        with contextlib.redirect_stdout(result_io):
            compiled = compile(python_code, "<string>", "exec")
            exec(compiled, {}, local_vars)

            final_result = None

            if "main" in local_vars and asyncio.iscoroutinefunction(local_vars["main"]):
                final_result = await local_vars["main"]()

            else:
                try:
                    compiled_eval = compile(python_code, "<string>", "eval")
                except SyntaxError:
                    pass
                else:
                    final_result = eval(compiled_eval, {}, local_vars)

    except Exception as e:
        return {"code": python_code[:1000], "stdout": result_io.getvalue(), "result": None, "error": repr(e)}

    return {"code": python_code[:1000], "stdout": result_io.getvalue(), "result": final_result, "error": None}


# Try provide two tools for agent
agent.use_tools([add, python_code_executor])
# Try just use code executor
# agent.use_tools(python_code_executor)
# Try use nothing
# pass


@agent.auto_func
def calculate(formula: str) -> int:
    """
    Return result of {formula}.
    MUST USE TOOLS TO ENSURE THE ANSWER IS ACTUAL NO MATTER WHAT.
    """
    ...


result = calculate("3333+6666=?")
print(result)
