import discord
import random

from fpl_api import get_player_image, FplApi

fplApi = FplApi()


def transfer_balance_emojifier(transfer_balance: int) -> str:
    if transfer_balance > 0:
        emoji = "⬆"
    elif transfer_balance < 0:
        emoji = "⬇"
    else:
        emoji = ""

    transfer_difference = abs(transfer_balance)

    return emoji + " " + str(transfer_difference)



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
                                                              '' + str(point_info["points"]) + " points\n"

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

        team_player_info = ''

        for player in team_players[:5]:
            team_player_info += '**' + player["web_name"] + '** ' + str(player["form"]) + " Form, " + \
                                '£{:.1f}'.format(player["now_cost"] / 10) + ' million\n'

        self.title = team_info_dict['name'] + " Info"
        self.description = '⭐' * team_info_dict["strength"]
        self.set_thumbnail(url=team_logo_link)

        self.add_field(name="FPL Stats",
                       value=f"Total FPL points: {str(fpl_scores['total_points'])}\n"
                             f"Current FPL form: {fpl_scores['total_form']:.1f}\n"
                             f"FPL Strength: {fpl_scores['fpl_score']:.2f}")
        self.add_field(name='Inform players:',
                       value=team_player_info)


        matches = fplApi.view_fixtures_for_team(team_name)
        last_5_results = matches['results'][-5:]
        next_5_fixtures = matches['fixtures'][:5]

        result_info = ''
        for result in last_5_results:
            home_team = fplApi.view_team(result['team_h'] - 1)
            away_team = fplApi.view_team(result['team_a'] - 1)
            score = '**' + home_team["name"] + '** ' + str(result['team_h_score']) + ' - ' + \
                    str(result['team_h_score']) + ' **' + away_team["name"] + '** (GW ' + str(result['event']) + ')'
            result_info += score + '\n'

        fixture_info = ''
        for fixture in next_5_fixtures:
            home_team = fplApi.view_team(fixture['team_h'] - 1)
            away_team = fplApi.view_team(fixture['team_a'] - 1)
            fixture_info += '**' + home_team['name'] + '** vs **' + away_team['name'] +\
                            '** (GW ' + str(fixture['event']) + ')\n'

        self.add_field(name='Results:', value=result_info, inline=False)
        self.add_field(name='Fixtures:', value=fixture_info)

        team_shirt = fplApi.view_team_shirt(team_name)
        self.set_image(url=team_shirt)

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

        self.title = home_team['name'] + ' vs ' + away_team['name']
        self.add_field(name=home_team['name']+':',
                       value='⭐' * home_strength + '\n' +\
                             str(home_attack) + ' attack\n'+\
                             str(home_defence) + ' defence')

        self.add_field(name=away_team['name']+':',
                       value='⭐' * away_strength + '\n' +\
                             str(away_attack) + ' attack\n'+\
                             str(away_defence) + ' defence')

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
        average_points = total_points/played_gameweeks

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
        self.set_thumbnail(url=fplApi.view_team_logo(favourite_team-1))


        for week in history['current']:
            if week['event'] == gameweek:
                gameweek_details = week

        self.add_field(name=f'Gameweek {str(gameweek)} Performance',
                       value=f"Rank: {str(gameweek_details['rank'])}\n"
                             f"Total Points: {str(gameweek_details['points'])}\n"
                             f"Team value: £{(gameweek_details['value'] - gameweek_details['bank'])/10:.1f} million\n"
                             f"Bank balance: £{(gameweek_details['bank']/10):.1f} million\n")

        player_info = '**Main Team**\n'
        for i, player in enumerate(team["picks"]):
            if i==11:
                player_info += '**Subs**\n'

            player_performance = fplApi.view_player_on_gameweek(player['element'], gameweek)
            player_details = fplApi.view_player(player['element'], no_api=True)
            points = player_performance['total_points']
            player_info += f"*{player_details['full_name']}*: {str(points*player['multiplier'])} points"
            player_info += ' (c)\n' if player['is_captain'] else (' (vc)\n' if player['is_vice_captain'] else '\n')


        self.add_field(name=f'Gameweek {str(gameweek)} Team', value=player_info, inline=False)


        transfer_list = []
        for transfer in transfers:
            if transfer['event'] == gameweek:
                transfer_list.append(transfer)

        if transfer_list:
            transfer_info = ''
            for tranfer in transfer_list:
                player_in = fplApi.view_player(tranfer['element_in'], no_api=True)['full_name']
                player_out = fplApi.view_player(tranfer['element_out'], no_api=True)['full_name']
                transfer_info += f'IN: **{player_in}** (£{tranfer["element_in_cost"]/10:.1f} mil),' \
                                 f' OUT: **{player_out}** (£{tranfer["element_out_cost"]/10:.1f} mil)\n'
            self.add_field(name=f"Gameweek {str(gameweek)} Transfers",
                           value=transfer_info)

            if len(self.fields[-1].value) > 1024:
                self.remove_field(-1)
                self.add_field(name=f"Transfers Unavailable",
                               value='Transfers not shown due to being over character limit')