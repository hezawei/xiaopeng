import asyncio


async def task(name, delay):
    """ 编写测试用例"""
    print(f"Task {name} started")
    await asyncio.sleep(delay)
    print(f"Task {name} finished")


async def main():
    tasks = []
    for i in range(10):
        t = task(i, 10)
        tasks.append(t)

    await asyncio.gather(*tasks)
    # # 创建任务并并发执行
    # task1 = asyncio.create_task(task("A", 2))
    # task2 = asyncio.create_task(task("B", 1))
    #
    # # 等待任务完成
    # await task1
    # await task2


asyncio.run(main())