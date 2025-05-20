import asyncio

# 协程

async def main():
    print("Hello World")
async def testing():
    a = main()
    b = main()
    x = [a, b]
    await asyncio.gather(*x)

async def t1():
    await main()

if __name__ == "__main__":
    asyncio.run(main())