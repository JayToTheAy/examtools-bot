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
import hamstudy
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
        await self.tree.sync(guild=MY_GUILD)
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

#region Find Exams
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
    start_date: str = str(datetime.datetime.now(datetime.UTC)),
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
        response_json = hamstudy.get_sessions(
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
                format_exam_field(embed, session)
                num_entries += 1
            else:
                break

        await interaction.response.send_message(embed=embed, ephemeral=not post)


def format_exam_field(embed: discord.Embed, session: dict):
    """Generate a field for an exam session"""

    url = 'https://hamstudy.org' + session['infoLink']
    title = f'Team {session["teamId"]}'
    exam_hammertime = f"<t:{time_to_unix_epoch_utc(session['date'])}:f>"

    # check if we're in-person before grabbing an address
    address = session['formatted_addr'] if session['online_session'] is False else 'Online'

    team_body = f"**When**: {exam_hammertime}\n\
        **Where**: {address}\n\
        **Pre-Registration Required**: {session['prereg_required']}\n\
        **Remote**: {session['online_session']}\n\
        **VEC**: {VEC(session['vec']).name}\n\
        **Fee**: ${session['test_fee']}\n\
        [**Session Link**]({url})"

    embed.add_field(name=title,
                    value=team_body,
                    inline=False)
#endregion

#region ULS lookup

@client.tree.command()
async def uls(interaction: discord.Interaction,
                lookup_id: str,
                post: bool = False):
    """Lookup a callsign or FRN's ULS data via the ExamTools API"""
    print("Got ULS lookup request on ", datetime.datetime.now())
    # verify parameters
    if interaction is None or lookup_id == "" or post is None:
        print(str(interaction), lookup_id, post)
        raise Exception("Invalid parameters")

    json, status_code = hamstudy.get_uls(lookup_id)
    if status_code == 404:
        await interaction.response.send_message("Unable to find anything for id: " + lookup_id,
                                                ephemeral=True)
    else:

        embed = discord.Embed()
        embed.title = "Data for " + lookup_id + ":"
        # call
        callsign = json.get('callsign')
        if callsign is not None:
            embed.add_field(name='Callsign',
                            value=callsign,
                            inline = True)

        # frn
        frn = json.get('frn')
        if frn is not None:
            embed.add_field(name='FRN',
                            value=frn,
                            inline=True)

        # licensee id
        lid = json.get('licensee_id')
        if lid is not None:
            embed.add_field(name='Licensee ID',
                            value=lid,
                            inline=True)

        # name
        name = make_name(json)
        if name is not None and name != '':
            embed.add_field(name='Name',
                            value=name,
                            inline=True)

        # address
        address = json.get('address')
        if address is None or address == '':
            address = f'PO Box {json.get("pobox")}'

        address += "\n" + json.get('city') + ", " + json.get('state') + " " + json.get('zip')
        embed.add_field(name='Address',
                        value=address,
                        inline=True)

        # applicant type
        applicant_type = json.get('applicant_type')
        if applicant_type is not None:
            embed.add_field(name='Applicant Type',
                            value=applicant_type,
                            inline=True)

        # license class
        license_class = json.get('license_class')
        if license_class is not None and license_class != '':
            embed.add_field(name='License Class',
                            value=license_class,
                            inline=True)

        # previous license class
        prev_license_class = json.get('prev_license_class')
        if prev_license_class is not None and prev_license_class != '':
            embed.add_field(name='Prev License Class',
                            value=prev_license_class,
                            inline=True)

        # license status
        license_status = json.get('license_status')
        if license_status is not None and license_status != '':
            embed.add_field(name='License Status',
                            value=license_status,
                            inline=True)

        # grant date
        grant_date = json.get('grant_date')
        if grant_date is not None:
            embed.add_field(name='Grant Date',
                            value=f"<t:{time_to_unix_epoch_utc(grant_date)}:f>",
                            inline=True)

        # expiry date
        expiry_date = json.get('expired_date')
        if expiry_date is not None:
            embed.add_field(name='Expiry Date',
                            value=f"<t:{time_to_unix_epoch_utc(expiry_date)}:f>",
                            inline=True)

        # effective date
        effective_date = json.get('effective_date')
        if effective_date is not None:
            embed.add_field(name='Effective Date',
                            value=f"<t:{time_to_unix_epoch_utc(effective_date)}:f>",
                            inline=True)

        # cancelled date
        cancelled_date = json.get('cancellation_date')
        if cancelled_date is not None:
            embed.add_field(name='Cancellation Date',
                            value=f"<t:{time_to_unix_epoch_utc(cancelled_date)}:f>",
                            inline=True)

        # BQQ
        basic_qual = json.get('bqqResponse')
        if basic_qual is not None and basic_qual != '':
            embed.add_field(name='Basic Qualification',
                            value=basic_qual,
                            inline=True)

        # is_revoked
        is_revoked = json.get('is_revoked')
        if is_revoked is not None and is_revoked != '':
            embed.add_field(name='Is Revoked?',
                            value=is_revoked,
                            inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=not post)
    return

def make_name(json: dict) -> str:
    """Assembles name from json for uls lookups"""
    last_name = json.get('last_name')
    first_name = json.get('first_name')
    middle_initial = json.get('middle_initial')
    suffix = json.get('suffix')

    full_name = ''

    if last_name is not None and last_name != '':
        full_name += last_name
    if first_name is not None and first_name != '':
        full_name += f", {first_name}"
    if middle_initial is not None and middle_initial != '':
        full_name += f" {middle_initial}"
    if suffix is not None and suffix != '':
        full_name += f"{suffix}"

    return full_name

#endregion

#region General Functions
def time_to_unix_epoch_utc(a_time: str) -> int:
    """Convert a time as returned by HamStudy to UTC"""
    # timestamp() assumes naive datetimes are in local time, so let's inform it it's in utc
    dt = datetime.datetime.strptime(a_time, '%Y-%m-%dT%H:%M:%S.000Z')\
    .replace(tzinfo=datetime.timezone.utc)
    return int(dt.timestamp())
#endregion

@client.tree.command()
async def refresh(interaction: discord.Interaction, guild_id: str = None):
    """Sync command tree for a specified guild, or globally."""
    if interaction.user.id != int(config.OWNER_ID):
        await interaction.response.send_message('You must be the owner to use this command!',
                                                ephemeral=True)
        return

    print(f'Syncing for {guild_id if guild_id is not None else 'Global'}...')
    if guild_id is not None:
        guild = discord.Object(id=guild_id)
        await tree.sync(guild=guild)
    else:
        await tree.sync()

    await interaction.response.send_message("Commands have been synced globally. This may take up to an hour to propagate.",
                                                    ephemeral=True)

if __name__ == "__main__":
    client.run(config.TOKEN)
