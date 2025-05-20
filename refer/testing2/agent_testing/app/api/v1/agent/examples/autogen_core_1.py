import asyncio

from autogen_core import SingleThreadedAgentRuntime, type_subscription, DefaultTopicId

from dataclasses import dataclass

from autogen_core import AgentId, MessageContext, RoutedAgent, message_handler
from pydantic import BaseModel

# https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/message-and-communication.html
# 自定义消息类型（@dataclass或者继承BaseModel的类）
@dataclass
class MyMessageType:
    source: str
    content: str

class ResponseMessage(BaseModel):
    content: str

# 装饰器作用：订阅一个主题，名称叫 testcase_generator_topic_type
@type_subscription(topic_type="testcase_generator_topic_type")
class TestCaseGenerator(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Generator")

    # 参数名第一个必须叫 message，参数类型可以随便定义(@dataclass或者继承BaseModel的类)
    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> None:
        # 业务逻辑
        print(f"{self.id.type} received message: {message.content}")
        print("用例生成已经完成1")
        # 发送请求给用例评审智能体
        await self.publish_message(ResponseMessage(content="请开始评审用例"),
                                   topic_id=DefaultTopicId(type="testcase_review_topic_type"))

    @message_handler
    async def handle_my_message_type2(self, message: ResponseMessage, ctx: MessageContext) -> None:
        # 业务逻辑
        print(f"{self.id.type} received message: {message.content}")
        print("用例生成已经完成2")

@type_subscription(topic_type="testcase_review_topic_type")
class TestCaseReview(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Review")

    @message_handler
    async def handle_my_message_type(self, message: ResponseMessage, ctx: MessageContext) -> None:
        # 业务逻辑
        print(f"{self.id.type} received message: {message.content}")

async def main1():

    # 直接向某个agent发送消息
    runtime = SingleThreadedAgentRuntime()
    # 注册agent到运行时环境，名称是my_agent
    await TestCaseGenerator.register(runtime, "testcase", lambda: TestCaseGenerator())
    await TestCaseReview.register(runtime, "review", lambda: TestCaseReview())
    runtime.start()
    msg =MyMessageType(source="user", content="Hello, World!")
    # 向运行时环境中的 type=testcase 的 agent 发送消息
    # send_message  可以等待 agent 处理完成，并返回结果，接收返回结果（阻塞调用）
    kk = await runtime.send_message(msg, AgentId("testcase", "default"))
    print(kk)
    msg = MyMessageType(source="user", content="你好")
    await runtime.send_message(msg, AgentId("review", "default"))

async def main2():
    # 直接向topic 发送消息
    runtime = SingleThreadedAgentRuntime()
    # 注册agent到运行时环境，名称是my_agent
    await TestCaseGenerator.register(runtime, "testcase", lambda: TestCaseGenerator())
    await TestCaseReview.register(runtime, "review", lambda: TestCaseReview())
    runtime.start()
    msg =MyMessageType(source="user", content="Hello, World!")
    # 向运行时环境中的 type=testcase 的 agent 发送消息
    # 不会等待 agent 处理完成，也获取不到结果，不会阻塞调用
    await runtime.publish_message(msg, topic_id=DefaultTopicId(type="testcase_generator_topic_type"))

    # await runtime.publish_message(ResponseMessage(content="哈哈"), topic_id=DefaultTopicId(type="testcase_generator_topic_type"))
    # msg = MyMessageType(source="user", content="你好")
    # await runtime.publish_message(msg, topic_id=DefaultTopicId(type="testcase_review_topic_type"))

    # 等待空闲时停止运行（没有消息传递、没有智能体代码运行）
    await runtime.stop_when_idle()  # 休眠状态一直等待环境结束

asyncio.run(main2())