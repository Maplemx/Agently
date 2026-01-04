from fastapi import FastAPI
from pydantic import BaseModel
from flow import dump_flow

app = FastAPI()


class TestData(BaseModel):
    int_number: int


@app.post("/test")
async def test(data: TestData):
    return await dump_flow().async_start(data.int_number)


if __name__ == "__main__":
    import uvicorn

    print("Start serving on port 15365...")
    uvicorn.run(app, host="0.0.0.0", port=15365)
