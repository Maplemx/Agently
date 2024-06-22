import asyncio
import threading
from concurrent.futures import Future

def run_async(coro):
  """
  在新的事件循环中运行异步任务并返回结果。
  
  参数:
  coro: 协程对象
  
  返回:
  协程的结果
  """
  # 如果是已经在一个事件循环中，尝试另起一个线程，在该线程中建新的事件循环来执行协程（一个线程里只能有一个事件循环）
  future = Future()

  def runner(coro, future):
    try:
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      result = loop.run_until_complete(coro)
      future.set_result(result)
    except Exception as e:
      future.set_exception(e)
    finally:
      loop.close()

  thread = threading.Thread(target=runner, args=(coro, future))
  thread.start()
  thread.join()

  return future.result()