import asyncio
import argparse
from requirement_analysis_agent import RequirementAnalysisAgent
from autogen_agentchat.ui import Console

async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='需求分析系统')
    parser.add_argument('--file', type=str, required=True, help='需求文档路径')
    args = parser.parse_args()

    # 创建需求分析智能体
    agent = RequirementAnalysisAgent(files=[args.file])
    team = await agent.create_team()

    # 运行需求分析并输出结果
    print(f"开始分析需求文件: {args.file}")
    await Console(team.run_stream(task="开始需求分析"))
    print("需求分析完成")

if __name__ == "__main__":
    asyncio.run(main())


