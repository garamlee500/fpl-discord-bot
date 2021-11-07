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
        player_gameweek_points = fplApi.view_player_gameweek_ponits(player_id, gameweek)

        team = fplApi.view_team(player_dict["team"]-1)

        # replace jpg, with png (for some reason)
        player_image_link = player_dict["photo"][:-4] + ".png"
        team_logo_link = fplApi.view_team_logo(player_dict["team"]-1)

        self.title = player_dict["first_name"] + " " + player_dict["second_name"] + "'s profile!"
        self.set_image(url= get_player_image(player_image_link))
        self.set_thumbnail(url=team_logo_link)

        team_name = team["name"]
        self.add_field(name="Basic info", value=f"Team: {team_name}\n"
                                                f"Cost: £{(player_dict['now_cost']/10):.1f} million", inline=False)

        if player_dict["news"] != "":
            self.add_field(name="News:", value="**"+player_dict["news"]+"**", inline=False)

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

        discipline_text = ''
        if player_gameweek_info['yellow_cards'] > 0 :
            discipline_text = f"**{player_gameweek_info['yellow_cards']} yellow card given **"

        if player_gameweek_info['red_cards'] > 0:
            discipline_text += f"**Red card given**"

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
                       value=f"Cost on gameweek: £{(player_gameweek_info['value']/10):.1f} million\n"
                             f"Transfers in: {player_gameweek_info['transfers_in']}\n"
                             f"Transfers out: {player_gameweek_info['transfers_out']}\n"
                             f"Net transfers: "
                             f"{transfer_balance_emojifier(player_gameweek_info['transfers_balance'])}\n"
                             f"Selected by: {str(player_gameweek_info['selected'])}",
                            inline=True)

        '''
                self.add_field(name=f"Gameweek {str(gameweek)} performance:",
                               value=f"**{home_team['name']} {str(player_gameweek_info['team_h_score'])} - "
                                     f"{str(player_gameweek_info['team_a_score'])} {away_team['name']}**\n"
                                     f"Points Scored: {player_gameweek_info['total_points']}\n"
                                     f"Minutes Played: {player_gameweek_info['minutes']}\n"
                                     f"{player_gameweek_info['goals_scored']} goals, {player_gameweek_info['assists']} assists\n\n"
                                     f"{player_gameweek_info['bps']} points on bonus point system, "
                                     f"{player_gameweek_info['bonus']} bonus points awarded\n\n"
                                     +discipline_text,
                               inline=True)'''