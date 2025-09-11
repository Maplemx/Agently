from fastmcp import FastMCP

app = FastMCP("calculator")


@app.tool
def add(first_number: float, second_number: float) -> float:
    """
    加法计算器：计算{first_number}和{second_number}的和，给出保留2位小数的结果
    """
    return round(first_number + second_number, 2)


if __name__ == "__main__":
    app.run(transport="stdio", show_banner=False)
