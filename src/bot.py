import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext, ButtonStyle, client, ComponentContext
from discord_slash.utils.manage_commands import create_choice


from datetime import datetime
from difflib import get_close_matches

from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow, \
    wait_for_component

from fpl_api import FplApi
from custom_embed import PlayerProfileEmbed

bot = commands.Bot(command_prefix="your mother", help_command=None)
slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)

# Open discordKey.txt and extract discord bot key
file = open('discordKey.txt', 'r')
DISCORD_KEY = file.readlines()[0]
file.close()

fplApi = FplApi()
team_list = fplApi.view_teamname_list()


# When the bot is ready
# Print out that it is ready with datetime it was logged in on
@bot.listen('on_ready')
async def on_ready():
    time_info = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    print(f'We have logged in as {bot.user.name} on {time_info}')

    await fplApi.regular_updater(60)


@slash.slash(
    name="team_info",
    description="View basic team stats",
    options=[
        {
            "name": "team_name",
            "description": "Name of team to view",
            "required": False,
            "type": 3,
            "choices": [create_choice(name=team, value=team) for team in team_list]
        }
    ]
)
async def team_info(ctx: SlashContext, team_name: str = team_list[0]):
    team_info_dict = fplApi.view_team(team_name)
    await ctx.send(str(team_info_dict))


@slash.slash(
    name="player_search",
    description="Search for a player's profile",
    options=[
        {
            "name": "player_last_name",
            "description": "Last name of player to search for",
            "type": 3,
            "required": True
        }
    ]
)
async def player_info(ctx: SlashContext, player_last_name: str):

    gameweek = fplApi.gameweek

    # Get list of all "web names"
    all_web_names = list(fplApi.playername_id_dict.values())

    # Find most similar names
    similar_names = get_close_matches(player_last_name, all_web_names, n=20)

    if len(similar_names) == 0:
        await ctx.send("No search results!")
        return

    player_ids = []

    # Go through list and get each players' id
    for key in fplApi.playername_id_dict:
        if fplApi.playername_id_dict[key] in similar_names:
            player_ids.append(key)

    player_dicts = []

    # Go through and get all player details
    for player_id in player_ids:
        player_dicts.append(fplApi.view_player(player_id))

    # Create select allowing user to grow through search results
    select = create_select(
        [ create_select_option(label=player["web_name"],
                              description=player["first_name"] + " " + player["second_name"],
                              value = str(player_dicts.index(player)))
         for player in player_dicts ],
        placeholder="Choose player",
        min_values=1,
        max_values=1,
    )

    actionrow =create_actionrow(select)
    await ctx.send(embed=PlayerProfileEmbed(player_ids[0], gameweek), components=[actionrow])

    while True:
        select_ctx: ComponentContext = await wait_for_component(bot, components=actionrow)

        selected_items_list_position = select_ctx.selected_options[0]
        await select_ctx.edit_origin(embed= PlayerProfileEmbed(player_ids[int(selected_items_list_position)],
                                                               gameweek))


if __name__ == "__main__":
    bot.run(DISCORD_KEY)
