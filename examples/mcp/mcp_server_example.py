import httpx
from mcp.server.fastmcp import FastMCP

mcp_server = FastMCP("Cocktail Info")

@mcp_server.prompt()
async def look_up_cocktail_info_prompt(message: str) -> str:
    return f"Please check cocktail information in '{ message }'. Cocktail name MUST BE translated into English!"

@mcp_server.tool()
async def look_up_cocktail_info(cocktail_name:str):
    """Look up cocktail information by name.
The name MUST BE translated into English and the name MUST BE the basic name of cocktail.
For Example:
'Margarita' is RIGHT!
'Spicy Mango Margarita' is WRONG!"""
    return (
        httpx.get(
            "https://www.thecocktaildb.com/api/json/v1/1/search.php",
            params={
                "s": cocktail_name,
            }
        )
        .content.decode()
    )

if __name__ == "__main__":
    mcp_server.run()