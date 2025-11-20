from fastmcp import FastMCP
from typing import Any

app = FastMCP("calculator")


@app.tool
def add(first_number: float, second_number: float) -> float:
    """
    Calculator for adding: return the sum of {first_number} and {second_number} with two decimal places.
    """
    return round(first_number + second_number, 2)


if __name__ == "__main__":
    app.run(
        show_banner=False,
        transport="http",
        port=8080,
    )
    # app.run(show_banner=False)
