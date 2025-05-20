import asyncio

from autogen_agentchat.ui import Console
from autogenstudio.teammanager import TeamManager

# Initialize the TeamManager
manager = TeamManager()

asyncio.run(Console(manager.run_stream(task="编写一篇关于AI的文言文", team_config="team_studio.json")))
