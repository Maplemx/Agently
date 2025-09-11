from fastmcp import FastMCP

app = FastMCP("calculator")


@app.tool
def add(first_number: float, second_number: float) -> float:
    """
    Add Calculator：return the result of {first_number} add {second_number}
    """
    return round(first_number + second_number, 2)


if __name__ == "__main__":
    app.run(transport="stdio", show_banner=False)
