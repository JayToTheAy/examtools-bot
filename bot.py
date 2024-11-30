"""The bones that make the app-command bot on discord

Copyright (C) 2024  Jacob Humble

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from enum import Enum
import datetime
import discord
from discord import app_commands
import requests
import sessions
import config

MY_GUILD = discord.Object(id=config.MY_GUILD_ID)

EXAM_TYPE = Enum('Exam Type', [
    ('Remote', 'remote'),
    ('In-Person', 'inperson'),
    ('All', 'all')
])

VEC = Enum('VEC', [
    ('Anchorage ARC', 'anchorage'),
    ('ARRL-VEC', 'arrl'),
    ('CAVEC', 'cavec'),
    ('GEARS', 'golden'),
    ('GLAARG', 'lagroup'),
    ('Jefferson ARC', 'jefferson'),
    ('Laurel ARC, Inc', 'laurel'),
    ('MRAC VEC, Inc', 'mrac'),
    ('MO-KAN VEC','mo-kan'),
    ('Sandarc-VEC', 'sandarc'),
    ('Sunnyvale VEC', 'sunnyvale'),
    ('W4VEC', 'w4vec'),
    ('W5YI', 'w5yi'),
    ('Western Carolina ARS VEC', 'west-carolina')
])

class MyClient(discord.Client):
    """Client class"""
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=MY_GUILD)
        print(f'Copied globals to guild {MY_GUILD.id}')

intents = discord.Intents.default()
client = MyClient(intents=intents)
tree = client.tree

@client.event
async def on_ready():
    """On-ready event"""
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')

@client.tree.command()
async def hello(interaction: discord.Interaction):
    """Says hello!"""
    await interaction.response.send_message(f'Hi, {interaction.user.mention}')

@client.tree.command()
@app_commands.describe(
    zipcode = "Search for exams near this ZIP Code",
    geo_long = "Search for exams near this longitude",
    geo_lat = "Search for exams near this latitude",
    max_distance = "Only return exams this distance or closer, in miles",
    vec = "Search for exams by VEC",
    team_id = "Search for exams by team ID",
    start_date = "Earliest date to show exams for",
    end_date = "Latest date to show exams for",
    exam_type = "In-Person, Remote, or All",
    max_fee = "Only return exams with a fee less than this",
    include_full = "Include sessions that are full?",
    post = "Post result in chat?"
)
async def findexam(
    interaction: discord.Interaction,
    zipcode: str = None,
    geo_long: str = None,
    geo_lat: str = None,
    max_distance: str = None,
    vec: VEC = None,
    team_id: str = None,
    start_date: str = None,
    end_date: str = None,
    exam_type: EXAM_TYPE = None,
    max_fee: str = None,
    include_full: bool = False,
    post: bool = False
):
    """Returns the first five exams on ExamTools matching your criteria."""
    #validate parameters
    print("Got a request at ", datetime.datetime.now())
    vec = vec.value if vec is not None else None
    exam_type = exam_type.value if exam_type is not None else None
    if start_date is not None:
        try:
            datetime.datetime.fromisoformat(start_date)
        except ValueError:
            await interaction.response.send_message("Start date was not in an ISO 8601 compliant format.\
                                                    Please re-enter it in a compliant format (i.e., YYYY-MM-DD).",
                                                    ephemeral=True)
            return

    if end_date is not None:
        try:
            datetime.datetime.fromisoformat(end_date)
        except ValueError:
            await interaction.response.send_message("End date was not in an ISO 8601 compliant format.\
                                                    Please re-enter it in a compliant format (i.e., YYYY-MM-DD).",
                                                    ephemeral=True)
            return
    try:
        response_json = sessions.get_sessions(
        zipcode,
        geo_long,
        geo_lat,
        max_distance,
        vec,
        team_id,
        start_date,
        end_date,
        exam_type,
        max_fee,
        include_full,
    )
    except requests.HTTPError:
        await interaction.response.send_message("Got a connection error, try again later.",
                                                ephemeral=True)
    else:
        embed = discord.Embed()
        embed.title = "Exams Found:"
        num_entries = 0
        for session in response_json:
            if num_entries < 5:
                field_formatter(embed, session)
                num_entries += 1
            else:
                break

        await interaction.response.send_message(embed=embed, ephemeral=not post)

def field_formatter(embed: discord.Embed, session: dict):
    """Generate a field for an exam session"""

    url = 'https://hamstudy.org' + session['infoLink']
    title = f'Team {session["teamId"]}'
    # timestamp() assumes naive datetimes are in local time, so let's inform it it's in utc
    exam_time = datetime.datetime.strptime(session['date'], '%Y-%m-%dT%H:%M:%S.000Z')\
    .replace(tzinfo=datetime.timezone.utc)
    exam_time_str = f"<t:{int(exam_time.timestamp())}:f>"

    # check if we're in-person before grabbing an address
    address = session['formatted_addr'] if session['online_session'] is False else 'Online'

    team_body = f"**When**: {exam_time_str}\n\
        **Where**: {address}\n\
        **Pre-Registration Required**: {session['prereg_required']}\n\
        **Remote**: {session['online_session']}\n\
        **VEC**: {VEC(session['vec']).name}\n\
        **Fee**: ${session['test_fee']}\n\
        [**Session Link**]({url})"

    embed.add_field(name=title,
                    value=team_body,
                    inline=False)

@tree.command(name='refresh', description='Owner only')
@app_commands.guilds(MY_GUILD)
async def refresh(interaction: discord.Interaction):
    """Refresh the tree."""
    if interaction.user.id == config.OWNER_ID:
        await tree.sync(guild=MY_GUILD)
        await tree.sync()
        print('Command tree synced.')
        await interaction.response.send_message("Commands have been synced globally.")
    else:
        await interaction.response.send_message('You must be the owner to use this command!')

if __name__ == "__main__":
    client.run(config.TOKEN)
