import asyncio

async def say_hello():
    print("Hello")
    await asyncio.sleep(1)
    print("World")
    return "但问智能欢迎您"
def sum(a, b):
    return a + b
async def main():
    s =  await say_hello()
    m = sum(100,2000)
    print(m)

asyncio.run(main())