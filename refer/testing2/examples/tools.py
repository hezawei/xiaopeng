
class Tools:
    def __init__(self):

        print("haha")

    @staticmethod
    def say():
        print("hello")

    def sum(self, a, b):
        return a + b
# 单例设计模式，该代码只会实例化一次(配置对象)
# tt = Tools()

def testing(**kwargs):
    # print(args[1])
    # print(type(args))
    # print(type(kwargs))
    # print(args)
    print(kwargs)
# s = (1,2,3,4,5)
# d = [1,2,3,4,5]
# testing(*d)
# testing(1,2,3,4,5)
d = {"a":1,"b":2,"c":3}
testing(**d)
testing(a=1,b=2,c=3)
