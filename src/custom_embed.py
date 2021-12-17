import uuid

import discord
import random

from discord_components import ButtonStyle
from discord_slash import SlashContext, ComponentContext
from discord_slash.utils.manage_components import create_select_option, create_select, create_actionrow, \
    wait_for_component, create_button

from fpl_api import get_player_image
from bot import fplApi, fplDatabase
from bet_processor import odd_finder


def underscore(string):
    return string.replace(' ', '_')


import json

emojis = {}
emoji_files = ['GOALIE_EMOJIS.json', 'LOGO_EMOJIS.json', 'SHIRT_EMOJIS.json', 'PLAYER_EMOJIS.json']
for emoji_file in emoji_files:
    emojis |= json.load(fp=open(emoji_file, 'r'))

def get_emoji_id(emoji_name):
    emoji = emojis[emoji_name]
    emoji = emoji.split(':')
    emoji_id = emoji[-1][:-1]
    return int(emoji_id)

def transfer_balance_emojifier(transfer_balance: int) -> str:
    if transfer_balance > 0:
        emoji = "⬆"
    elif transfer_balance < 0:
        emoji = "⬇"
    else:
        emoji = ""

    transfer_difference = abs(transfer_balance)

    return emoji + " " + str(transfer_difference)

def get_profile_pic(user: discord.user):
    if user.avatar:
        # get image link
        if user.is_avatar_animated():
            image_url = f'https://cdn.discordapp.com/avatars/{user.id}/{user.avatar}.gif' \
                        f'?size=256 '

        else:
            image_url = f'https://cdn.discordapp.com/avatars/{user.id}/{user.avatar}.png' \
                        f'?size=256 '
    else:
        user_discriminator = int(user.discriminator) % 5
        image_url = f'https://cdn.discordapp.com/embed/avatars/{user_discriminator}.png?size=256'
    return image_url

def predict_goals(attack: int, defence: int) -> int:
    """
    Predict the number of goals based on attack and defence strength, using interpolation by desmos!
    (might collect data in database later to more accurately calculate this
    :param attack:
    :param defence:
    :return:
    """
    attack_advantage = attack - defence
    goals = round(attack_advantage * 0.007874 + 1.25)

    return goals if goals > 0 else 0


# Default embed settings
class FplEmbed(discord.Embed):
    def __init__(self):
        super().__init__()
        self.type = 'rich'
        # Use random colour
        self.colour = discord.Colour(int('%06x' % random.randrange(16 ** 6), 16))
        self.set_author(name='fpl-discord-bot',
                        url='https://github.com/garamlee500/fpl-discord-bot',
                        icon_url="https://raw.githubusercontent.com/garamlee500/fpl-discord-bot/main/fpl.png?c=3")


class PlayerProfileEmbed(FplEmbed):
    def __init__(self, player_id: int, gameweek: int):
        super().__init__()
        player_dict = fplApi.view_player(player_id)

        player_gameweek_info = fplApi.view_player_on_gameweek(player_id, gameweek)
        player_gameweek_points = fplApi.view_player_gameweek_points(player_id, gameweek)

        while not player_gameweek_info:
            gameweek -= 1
            player_gameweek_info = fplApi.view_player_on_gameweek(player_id, gameweek)
            player_gameweek_points = fplApi.view_player_gameweek_points(player_id, gameweek)

        team = fplApi.view_team(player_dict["team"] - 1)

        # replace jpg, with png (for some reason)
        player_image_link = player_dict["photo"][:-4] + ".png"
        team_logo_link = fplApi.view_team_logo(player_dict["team"] - 1)

        self.title = player_dict["full_name"] + "'s profile!"
        self.set_image(url=get_player_image(player_image_link))
        self.set_thumbnail(url=team_logo_link)

        team_name = team["name"]
        self.add_field(name="Basic info", value=f"Team: {team_name}\n"
                                                f"Position: {player_dict['position']}\n"
                                                f"Cost: £{(player_dict['now_cost'] / 10):.1f} million", inline=False)

        if player_dict["news"] != "":
            self.add_field(name="News:", value="**" + player_dict["news"] + "**", inline=False)

        self.add_field(name="Performance", value=f"Form: {player_dict['form']}\n"
                                                 f"Total Points: {player_dict['total_points']}\n"
                                                 f"Points per Match: {player_dict['points_per_game']}\n"
                                                 f"Form Value: {player_dict['value_form']}\n"
                                                 f"Value For Season: {player_dict['value_season']}", inline=False)

        this_gameweek_transfer_balance = player_dict['transfers_in_event'] - player_dict['transfers_out_event']
        self.add_field(name="Popularity",
                       value=f"Selected by: {player_dict['selected_by_percent']}%\n"
                             f"Transfers in this gameweek: {player_dict['transfers_in_event']}\n"
                             f"Transfers out this gameweek: {player_dict['transfers_out_event']}\n"
                             f"Net transfers this gameweek: "
                             f"{transfer_balance_emojifier(this_gameweek_transfer_balance)}", inline=False)

        if player_gameweek_info["was_home"]:
            home_team = {'name': team_name}
            # Away team is opposing team if player is at home. Team ids are shifted by 1
            away_team = fplApi.view_team(player_gameweek_info["opponent_team"] - 1)
        else:
            home_team = fplApi.view_team(player_gameweek_info["opponent_team"] - 1)
            away_team = {'name': team_name}

        gameweek_point_info = ''

        for point_info in player_gameweek_points:
            gameweek_point_info += str(point_info["value"]) + " " \
                                                              "" + point_info["identifier"].replace('_', ' ') + ': ' \
                                                                                                                '' + str(
                point_info["points"]) + " points\n"

        self.add_field(name=f"Gameweek {str(gameweek)} performance:",
                       value=f"**{home_team['name']} {str(player_gameweek_info['team_h_score'])} - "
                             f"{str(player_gameweek_info['team_a_score'])} {away_team['name']}**\n" +
                             gameweek_point_info + f'***Total Points: {player_gameweek_info["total_points"]}***')

        self.add_field(name=f"Other gameweek {str(gameweek)} stats:",
                       value=f"Cost on gameweek: £{(player_gameweek_info['value'] / 10):.1f} million\n"
                             f"Transfers in: {player_gameweek_info['transfers_in']}\n"
                             f"Transfers out: {player_gameweek_info['transfers_out']}\n"
                             f"Net transfers: "
                             f"{transfer_balance_emojifier(player_gameweek_info['transfers_balance'])}\n"
                             f"Selected by: {str(player_gameweek_info['selected'])}",
                       inline=True)


class TeamProfileEmbed(FplEmbed):
    def __init__(self, team_name: str):
        super().__init__()

        team_info_dict = fplApi.view_team(team_name)
        team_logo_link = fplApi.view_team_logo(team_name)
        team_players = fplApi.view_team_players(team_name)
        fpl_scores = fplApi.view_team_fpl_score(team_name)
        shirt_emoji = emojis[underscore(team_name) + '_shirt']
        goalie_emoji = emojis[underscore(team_name) + '_goalie']

        team_player_info = ''

        for player in team_players[:5]:
            position = fplApi.main_data['element_types'][player['element_type']-1]['singular_name_short']
            try:
                emoji = emojis[str(player['id'])]
            except KeyError:
                emoji = shirt_emoji

            team_player_info += emoji + ' (' + position + ') ' + '**' + player["web_name"] + '** ' + \
                                str(player["form"]) + " Form, "+'£{:.1f}'.format(player["now_cost"] / 10) + ' million\n'

        self.title = team_info_dict['name'] + " Info "

        self.description = '⭐' * team_info_dict["strength"] +'\n'
        self.set_thumbnail(url=team_logo_link)

        self.add_field(name="FPL Stats",
                       value=f"Total FPL points: {str(fpl_scores['total_points'])}\n"
                             f"Current FPL form: {fpl_scores['total_form']:.1f}\n"
                             f"FPL Strength: {fpl_scores['fpl_score']:.2f}\n")
        self.add_field(name='Inform players:',
                       value=team_player_info)

        matches = fplApi.view_fixtures_for_team(team_name)
        last_5_results = matches['results'][-5:]
        next_5_fixtures = matches['fixtures'][:5]

        result_info = ''
        for result in last_5_results:
            home_team = fplApi.view_team(result['team_h'] - 1)
            home_emoji = emojis[underscore(home_team['name'])]
            away_team = fplApi.view_team(result['team_a'] - 1)
            away_emoji = emojis[underscore(away_team['name'])]
            score = home_emoji + ' **' + home_team["name"] + '** ' + str(result['team_h_score']) + ' - ' + \
                    str(result['team_h_score']) + ' **' + away_team["name"] + ' ' + away_emoji +\
                    '** (GW ' + str(result['event']) + ')'
            result_info += score + '\n'

        fixture_info = ''
        for fixture in next_5_fixtures:
            home_team = fplApi.view_team(fixture['team_h'] - 1)
            home_emoji = emojis[underscore(home_team['name'])]
            away_team = fplApi.view_team(fixture['team_a'] - 1)
            away_emoji = emojis[underscore(away_team['name'])]
            fixture_info += home_emoji + ' **' + home_team['name'] + '** vs **' + away_team['name'] + \
                            ' ' + away_emoji + '** (GW ' + str(fixture['event']) + ')\n'

        self.add_field(name='Results:', value=result_info, inline=False)
        self.add_field(name='Fixtures:', value=fixture_info)

        team_shirt = fplApi.view_team_shirt(team_name)
        # self.set_image(url=team_shirt)


class ComparisonEmbed(FplEmbed):
    def __init__(self, home_team: str, away_team: str):
        super().__init__()
        home_team = fplApi.view_team(home_team)
        away_team = fplApi.view_team(away_team)

        home_attack = home_team['strength_attack_home']
        home_defence = home_team['strength_defence_home']
        home_strength = home_team['strength']
        away_attack = away_team['strength_attack_away']
        away_defence = away_team['strength_defence_away']
        away_strength = away_team['strength']

        home_goals = predict_goals(home_attack, away_defence)
        away_goals = predict_goals(away_attack, home_defence)

        self.title = emojis[underscore(home_team['name'])] + ' ' + home_team['name'] + ' vs ' + \
                     away_team['name'] + ' ' + emojis[underscore(away_team['name'])]
        self.add_field(name=home_team['name'] + ':',
                       value='⭐' * home_strength + '\n' + \
                             emojis[underscore(home_team['name']) + '_shirt'] + ' ' + str(home_attack) + ' attack\n' + \
                             emojis[underscore(home_team['name']) + '_goalie'] + ' ' + str(home_defence) + ' defence')

        self.add_field(name=away_team['name'] + ':',
                       value='⭐' * away_strength + '\n' + \
                             str(away_attack) + ' attack' + ' ' + emojis[underscore(away_team['name']) + '_shirt'] +
                             '\n' + str(away_defence) + ' defence' + ' ' +
                             emojis[underscore(away_team['name']) + '_goalie'])

        self.add_field(name="Score Prediction:",
                       value=f"{home_team['name']} {str(home_goals)} - {str(away_goals)} {away_team['name']}",
                       inline=False)


class FplTeamEmbed(FplEmbed):
    def __init__(self, manager_id: int, gameweek: int = fplApi.gameweek):
        super().__init__()
        manager = fplApi.get_fpl_manager(manager_id)

        if 'id' not in manager:
            self.title = "Manager not found!"
            return

        transfers = fplApi.get_fpl_transfers(manager_id)
        team = fplApi.get_fpl_team(manager_id, gameweek)
        history = fplApi.get_fpl_manager_history(manager_id)

        self.title = manager["name"]
        full_name = manager["player_first_name"] + ' ' + manager['player_last_name']
        if manager['player_region_iso_code_short'] in ['WA', 'EN', 'S1']:
            flag_name = {'WA': 'wales',
                         'EN': 'england',
                         'S1': 'scotland'}[manager['player_region_iso_code_short']]
        else:
            flag_name = 'flag_' + manager['player_region_iso_code_short'].lower()

        first_gameweek = manager["started_event"]
        self.description = full_name + ' :' + flag_name + ':' + '\n' \
                                                                f'First Gameweek: {str(first_gameweek)}'

        played_gameweeks = fplApi.gameweek - first_gameweek + 1
        total_points = manager['summary_overall_points']
        average_points = total_points / played_gameweeks

        transfer_points = 0
        sub_points = 0
        for week in history['current']:
            transfer_points += week['event_transfers_cost']
            sub_points += week['points_on_bench']

        self.add_field(name='Total Performance',
                       value=f"Total Points: {str(total_points)}\n"
                             f"Total Rank: {str(manager['summary_overall_rank'])}\n"
                             f"Average Points Per Gameweek: {average_points:.2f}\n"
                             f"Total Transfer Points: {str(transfer_points)}\n"
                             f"Total Bench Points: {str(sub_points)}")

        favourite_team = manager['favourite_team']
        self.set_thumbnail(url=fplApi.view_team_logo(favourite_team - 1))

        for week in history['current']:
            if week['event'] == gameweek:
                gameweek_details = week

        self.add_field(name=f'Gameweek {str(gameweek)} Performance',
                       value=f"Rank: {str(gameweek_details['rank'])}\n"
                             f"Total Points: {str(gameweek_details['points'])}\n"
                             f"Team value: £{(gameweek_details['value'] - gameweek_details['bank']) / 10:.1f} million\n"
                             f"Bank balance: £{(gameweek_details['bank'] / 10):.1f} million\n")

        team_info = ''
        sub_info = ''
        for i, player in enumerate(team["picks"]):
            if player['multiplier'] == 0:
                player['multiplier'] = 1
            player_performance = fplApi.view_player_on_gameweek(player['element'], gameweek)
            player_details = fplApi.view_player(player['element'], no_api=True)

            player_team = fplApi.view_team(player_details['team']-1)

            try:
                emoji = emojis[str(player_details['id'])]
            except KeyError:
                emoji = emojis[underscore(player_team['name'])+'_shirt']

            try:
                points = player_performance['total_points']
            except KeyError:
                points = '-'

            info = f"{emoji} **({player_details['position_short']})** *{player_details['full_name']}*:" \
                           f" {str(points * player['multiplier'])} points"
            info += ' (c)\n' if player['is_captain'] else (' (vc)\n' if player['is_vice_captain'] else '\n')

            if i>=11:
                sub_info += info
            else:
                team_info += info

        self.add_field(name=f'Gameweek {str(gameweek)} Team', value=team_info, inline=False)
        self.add_field(name=f'Gameweek {str(gameweek)} Subs', value=sub_info, inline=False)

        transfer_list = []
        for transfer in transfers:
            if transfer['event'] == gameweek:
                transfer_list.append(transfer)

        if transfer_list:
            transfer_info = ''
            for tranfer in transfer_list:
                player_in = fplApi.view_player(tranfer['element_in'], no_api=True)['full_name']
                player_out = fplApi.view_player(tranfer['element_out'], no_api=True)['full_name']
                transfer_info += f'IN: **{player_in}** (£{tranfer["element_in_cost"] / 10:.1f} mil),' \
                                 f' OUT: **{player_out}** (£{tranfer["element_out_cost"] / 10:.1f} mil)\n'
            self.add_field(name=f"Gameweek {str(gameweek)} Transfers",
                           value=transfer_info)

            if len(self.fields[-1].value) > 1024:
                self.remove_field(-1)
                self.add_field(name=f"Transfers Unavailable",
                               value='Transfers not shown due to being over character limit')

        self.url = f"https://fantasy.premierleague.com/entry/{str(manager_id)}/event/{str(gameweek)}"

class GamblingDashboard(FplEmbed):
    def __init__(self, user: discord.user):
        super().__init__()
        image_url = get_profile_pic(user)

        coins = fplDatabase.find_account_money(user.id)
        self.coins = coins
        self.set_thumbnail(url=image_url)
        self.title = f"{user.name}'s Gambling dashboard!"

        self.add_field(
            name='Profile',
            value=f"**Name:** {user.name}#{user.discriminator}\n"
                  f"**Coins**: {coins}"
        )


class MatchScorePredictor(GamblingDashboard):
    def __init__(self, user: discord.user):

        random_id = str(uuid.uuid1())
        super().__init__(user)
        self.odds = odd_finder('match_score')
        if self.odds == 0:
            self.odds = 5

        self.add_field(name='Match Score Predictor',
                       value="Try your hand at guessing the results of matches!"
                             f" All correct bets are currently timesed by {self.odds}",
                       inline=False)


        fixtures = fplApi.view_fixtures_on_gameweek(only_not_started=True)
        matches = []
        select_options = []

        match_difficulty_comments = {
            4: ['Should be a walk in the park for {}.',
                'Expect Goals, Goals and Goals for {}.',
                "{} won't need half their team.",
                'Easy as pie for {}.'],
            3: ['Not really a challenge for {} - expect goals',
                'Only one likely winner in this one.',
                '{} could win this on an off day.',
                "Could be aday for {} to rest some players",
                "{} really the only one winning this.",
                "{}'s goalkeeper will have a nice day"],
            2: ['{} is going to win this',
                "A surprise loss for {} is quite unlikely",
                "Would be close if {} didn't arrive.",
                "{} is probably winning this",
                "We could see a couple of {} goals!",
                "{} will win this most days"],
            1: ['{} is likely to win, but could go either way',
                "{} will get 3 points with usual form",
                '{} will have to beware a surprise loss',
                "{} will just get the win",
                "Quality slightly in the favor of {}",
                "Mabye a draw, but {} should win this.",
                "A match which {} should edge",
                "{} on a good day should just win this"],
            0: ['Two even teams, setting the stage for an exciting battle',
                'A draw is not unlikely - either team could win',
                "Two similar teams both looking for a win",
                "{} will hope to use home advantage in an even match",
                "Two teams probably heading towards a draw",
                "A match going down to the wire",
                "A drawish match."]
        }

        for i, match in enumerate(fixtures):
            home_team = fplApi.view_team(match['team_h']-1)['name']
            away_team = fplApi.view_team(match['team_a']-1)['name']

            home_team_advantage = match['team_a_difficulty'] - match['team_h_difficulty']



            if home_team_advantage >= 0:
                winning_team = home_team
            else:
                winning_team = away_team

            match_description = random.choice(match_difficulty_comments[abs(home_team_advantage)])
            match_description = match_description.format(winning_team)

            matches.append((home_team, away_team))


            select_options.append(create_select_option(label=f"Bet on {home_team} vs {away_team}",
                                                       description=match_description,
                                                       emoji={'name': underscore(winning_team),
                                                              'id': get_emoji_id(underscore(winning_team))},
                                                       value=str(i)))

        self.select = create_select(select_options,
                               placeholder='Choose the match to bet on!',
                               min_values=1,
                               max_values=1,
                               custom_id='match_select' + random_id)

        self.random_id = random_id
        self.action_row = create_actionrow(self.select)
    async def launch(self, ctx: SlashContext, component_ctx, bot, components=None):
        if components is None:
            components = []

        handling_selects = ['match_select' + self.random_id]
        current_select = 'match_select' + self.random_id

        components.append(self.action_row)

        await component_ctx.edit_origin(embed=self, components=components)

        fixtures = fplApi.view_fixtures_on_gameweek(only_not_started=True)

        while current_select in handling_selects:
            self.random_id = str(uuid.uuid1())

            component_ctx: ComponentContext = await wait_for_component(bot, components=components)
            if ctx.author == component_ctx.author:
                if component_ctx.component_id.startswith('home'):
                    return component_ctx

                if component_ctx.component_id == handling_selects[0]:
                    match = fixtures[int(component_ctx.selected_options[0])]
                    home_team = fplApi.view_team(match['team_h'] - 1)['name']
                    away_team = fplApi.view_team(match['team_a'] - 1)['name']
                    set_home_score_select = create_select(
                        [
                            create_select_option(label=str(i), value=str(i)) for i in range(0,11)
                        ],
                        custom_id='home_team_score'+self.random_id,
                        min_values=1,
                        max_values=1,
                        placeholder=f"Predict {home_team}'s score!"
                    )
                    set_away_score_select = create_select(
                        [
                            create_select_option(label=str(i), value=str(i)) for i in range(0, 11)
                        ],
                        custom_id='away_team_score'+self.random_id,
                        min_values=1,
                        max_values=1,
                        placeholder=f"Predict {away_team}'s score!"
                    )
                    coins_to_bet_select = create_select(
                        [
                            create_select_option(label=str(i), value=str(i)) for i in range(1, min(26, self.coins+1))
                        ],
                        custom_id='money_to_bet'+self.random_id,
                        min_values=1,
                        max_values=1,
                        placeholder=f"Select amount to bet"
                    )
                    buttons = [create_button(
                        style=ButtonStyle.green,
                        label='Submit bet!',
                        custom_id='submit_bet'+self.random_id
                    ),
                        create_button(
                            style=ButtonStyle.red,
                            label='Go back home!',
                            custom_id='home'+self.random_id
                        )
                    ]
                    components = [self.action_row]
                    components.append(create_actionrow(set_home_score_select))
                    components.append(create_actionrow(set_away_score_select))
                    components.append(create_actionrow(coins_to_bet_select))
                    components.append(create_actionrow(*buttons))
                    await component_ctx.edit_origin(embed=self, components=components)
            else:
                return component_ctx