import asyncio
import httpx
import time


async def request(index: int, user_input: str):
    start_time = time.time()
    print(
        f"No.{ index } Start:",
        start_time,
    )
    client = httpx.AsyncClient()
    response = await client.get(
        "http://127.0.0.1:8000/chat",
        params={"user_input": user_input},
        timeout=None,
    )
    print(f"No.{ index } Response:", response.content.decode())
    end_time = time.time()
    print(
        f"No.{ index } End:",
        end_time,
    )


async def main():
    tasks = []
    for i in range(5):
        await asyncio.sleep(0.5)
        tasks.append(
            asyncio.create_task(
                request(
                    i + 1,
                    "What is “奇变偶不变，符号看象限”?",
                )
            )
        )
    await asyncio.gather(*tasks)


asyncio.run(main())
