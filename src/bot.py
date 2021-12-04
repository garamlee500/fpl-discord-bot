import uuid

import discord
import requests
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord_slash import SlashCommand, SlashContext, ButtonStyle, client, ComponentContext
from discord_slash.utils.manage_commands import create_choice

from datetime import datetime
from difflib import get_close_matches

from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow, \
    wait_for_component, create_button

from fpl_api import FplApi
from database import FplDatabase

import tabulate

fplDatabase = FplDatabase()
fplApi = FplApi()

if __name__ == '__main__':
    from custom_embed import PlayerProfileEmbed, TeamProfileEmbed, ComparisonEmbed, FplTeamEmbed
    bot = commands.Bot(command_prefix="your mother", help_command=None)
    slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)

    # Open discordKey.txt and extract discord bot key
    file = open('discordKey.txt', 'r')
    DISCORD_KEY = file.readlines()[0]
    file.close()

    team_list = fplApi.view_teamname_list()


    # When the bot is ready
    # Print out that it is ready with datetime it was logged in on
    @bot.listen('on_ready')
    async def on_ready():
        time_info = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f'We have logged in as {bot.user.name} on {time_info}')

        await fplApi.regular_updater()


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
        await ctx.defer()
        await ctx.send(embed=TeamProfileEmbed(team_name))


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
        def create_buttons(is_first_gameweek, is_last_gameweek):
            return [
                create_button(
                    style=ButtonStyle.blue,
                    label='⬅ ️Previous Gameweek',
                    custom_id="Previous" + random_id,
                    disabled=is_first_gameweek
                ),
                create_button(
                    style=ButtonStyle.blue,
                    label='Next Gameweek ➡',
                    custom_id="Next" + random_id,
                    disabled=is_last_gameweek
                ),
            ]

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

        random_id = str(uuid.uuid1())

        current_player = player_dicts[0]
        current_player_id = player_ids[0]

        # Create select allowing user to grow through search results
        select = create_select(
            [create_select_option(label=player["web_name"],
                                  description=player["full_name"],
                                  value=str(player_dicts.index(player)))
             for player in player_dicts],
            placeholder="Choose player",
            min_values=1,
            max_values=1,
            custom_id="select" + random_id
        )

        buttons = create_buttons(gameweek == current_player["first_gameweek"],
                                 gameweek == fplApi.gameweek)

        selected_items_list_position = 0

        actionrow = create_actionrow(select)
        button_row = create_actionrow(*buttons)
        await ctx.send(embed=PlayerProfileEmbed(current_player_id, gameweek), components=[actionrow, button_row])

        while True:
            component_ctx: ComponentContext = await wait_for_component(bot, components=[actionrow, button_row])

            if component_ctx.custom_id == "select" + random_id:
                selected_items_list_position = component_ctx.selected_options[0]
                current_player_id = player_ids[int(selected_items_list_position)]
                current_player = player_dicts[int(selected_items_list_position)]
                await component_ctx.edit_origin(embed=PlayerProfileEmbed(current_player_id, gameweek))

            elif component_ctx.custom_id == "Next" + random_id:
                gameweek += 1

                buttons = create_buttons(gameweek == current_player["first_gameweek"],
                                         gameweek == fplApi.gameweek)
                button_row = create_actionrow(*buttons)
                await component_ctx.edit_origin(embed=PlayerProfileEmbed(current_player_id, gameweek),
                                                components=[actionrow, button_row])

            elif component_ctx.custom_id == "Previous" + random_id:
                gameweek -= 1

                buttons = create_buttons(gameweek == current_player["first_gameweek"],
                                         gameweek == fplApi.gameweek)
                button_row = create_actionrow(*buttons)
                await component_ctx.edit_origin(embed=PlayerProfileEmbed(current_player_id, gameweek),
                                                components=[actionrow, button_row])

    @slash.slash(
        name="team_leaderboard",
        description="Get a leaderboard of the best teams for fpl at the moment",

    )
    async def team_leaderboard(ctx: SlashContext):
        await ctx.defer()
        teams = []
        for team in team_list:
            teams.append(fplApi.view_team_fpl_score(team))

        teams = sorted(teams, key=lambda d: float(d['fpl_score']), reverse=True)
        teams_in_list = []
        for i, team in enumerate(teams):
            teams_in_list.append([team["team"], team['total_points'], team['total_form'], team['fpl_score']])

        leaderboard = tabulate.tabulate(teams_in_list, headers=["Team", "Total points", "Form", "Fpl Score"], tablefmt='presto')
        await ctx.send('```' + leaderboard + '```')

    @slash.slash(
        name="compare",
        description="Compare two teams",
        options=[
            {
                "name": "home_team",
                "description": "Name of home team",
                "required": True,
                "type": 3,
                "choices": [create_choice(name=team, value=team) for team in team_list]
            },
            {
                "name": "away_team",
                "description": "Name of away team",
                "required": True,
                "type": 3,
                "choices": [create_choice(name=team, value=team) for team in team_list]
            }
        ]
    )
    async def compare(ctx: SlashContext, home_team: str, away_team: str):
        await ctx.send(embed=ComparisonEmbed(home_team, away_team))

    # Check non-emoji maker, and make sure enough emoji slots
    @slash.slash(
        name="generate_emojis",
        description="Generate emojis for guild. Must have manage_emojis permission.",
        options=[
            {
                "name": "emoji_choice",
                "description": "Choice of emojis",
                "required": True,
                "type": 3,
                "choices":[
                    create_choice(name="Team Logos", value="Logos"),
                    create_choice(name="Team Shirts", value="Shirts"),
                    create_choice(name="Team Goalie Shirts", value="Goalie Shirts")
                ]
            }
        ]
    )
    @has_permissions(manage_emojis=True)
    async def generate_emojis(ctx: SlashContext, emoji_choice: str):
        emoji_count = 0
        for emoji in ctx.guild.emojis:
            if not emoji.animated:
                emoji_count += 1

        if ctx.guild.emoji_limit - emoji_count < 20:
            await ctx.send("Warning you need 20 emoji slots for this", hidden=True)
            return

        await ctx.defer()

        if emoji_choice == "Logos":
            for team in team_list:
                image = requests.get(fplApi.view_team_logo(team)).content
                team = team.replace(' ', '_')
                await ctx.guild.create_custom_emoji(name=team, image=image)
        elif emoji_choice == "Shirts":
            for team in team_list:
                image = requests.get(fplApi.view_team_shirt(team)).content
                team = team.replace(' ', '_')
                try:
                    await ctx.guild.create_custom_emoji(name=team + "_shirt", image=image)
                except Exception as e:
                    print(e)
        elif emoji_choice == "Goalie Shirts":
            for team in team_list:
                image = requests.get(fplApi.view_team_shirt(team, is_goalie=True)).content
                team = team.replace(' ', '_')
                await ctx.guild.create_custom_emoji(name=team + "_goalie", image=image)

        await ctx.send("Emojis succesfully generated!")

    @generate_emojis.error
    async def generate_emojis_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Warning! You need the manage_emojis permission for this.", hidden=True)

    @slash.slash(
        name="fantasy_team",
        description="View fpl team of a certain id. Click on points in fpl in a browser and copy big number in url.",
        options=[{"name": "manager_id",
                  "description": "Id of fpl manager",
                  "required": False,
                  "type":4,
                  }]
    )
    async def fantasy_team(ctx: SlashContext, manager_id: int = 0):

        if not manager_id:
            manager_id = fplDatabase.find_fpl_id(discord_id=ctx.author.id)
            if not manager_id:
                await ctx.send("No id sent or stored in database!")
                return
        profile = fplApi.get_fpl_manager(manager_id)
        def create_buttons(is_first_gameweek, is_last_gameweek):
            return [
                create_button(
                    style=ButtonStyle.blue,
                    label='⬅ ️Previous Gameweek',
                    custom_id="Previous" + random_id,
                    disabled=is_first_gameweek
                ),
                create_button(
                    style=ButtonStyle.blue,
                    label='Next Gameweek ➡',
                    custom_id="Next" + random_id,
                    disabled=is_last_gameweek
                ),
            ]

        random_id = str(uuid.uuid1())

        if 'id' not in profile:
            await ctx.send("Warning, player not found. This can sometimes happen during fpl maintenance breaks.", hidden=True)
            return
        current_gameweek = fplApi.gameweek

        buttons = create_buttons(current_gameweek==profile['started_event'], current_gameweek==fplApi.gameweek)
        button_row = create_actionrow(*buttons)
        await ctx.defer()
        message = await ctx.send(embed=FplTeamEmbed(manager_id, current_gameweek), components=[button_row])

        while True:
            component_ctx: ComponentContext = await wait_for_component(bot, components=button_row)
            if component_ctx.custom_id == "Next" + random_id:
                current_gameweek+=1
            elif component_ctx.custom_id == "Previous" + random_id:
                current_gameweek-=1
            await component_ctx.defer(edit_origin=True)

            buttons = create_buttons(True, True)
            button_row = create_actionrow(*buttons)
            await component_ctx.edit_origin(components=[button_row])

            buttons = create_buttons(current_gameweek == profile['started_event'], current_gameweek == fplApi.gameweek)
            button_row = create_actionrow(*buttons)
            await message.edit(embed=FplTeamEmbed(manager_id, current_gameweek), components=[button_row])

    @slash.slash(
        name="set_fpl_id",
        description="Set fpl account. In browser, press 'Points' and copy number in url.",
        options=[{"name": "fpl_id",
                  "description": "Id of fpl manager",
                  "required": True,
                  "type": 4,
                  }]
    )
    async def set_fpl_id(ctx: SlashContext, fpl_id: int):
        fplDatabase.set_fpl_id(discord_id=ctx.author.id, fpl_id=fpl_id)
        await ctx.send("Id Set Correctly! Try /fantasy_team !")

    bot.run(DISCORD_KEY)