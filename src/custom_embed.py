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
                        icon_url="https://raw.githubusercontent.com/garamlee500/fpl-discord-bot/main/fpl.png")


class PlayerProfileEmbed(FplEmbed):
    def __init__(self, player_id: int, gameweek: int):
        super().__init__()

        player_dict = fplApi.view_player(player_id)
        player_gameweek_info = fplApi.view_player_on_gameweek(player_id)

        # replace jpg, with png (for some reason)
        player_image_link = player_dict["photo"][:-4] + ".png"

        self.title = player_dict["first_name"] + " " + player_dict["second_name"] + "'s profile!"
        self.set_image(url= get_player_image(player_image_link))


        team_name = fplApi.view_team(player_dict["team"] - 1)["name"]
        self.add_field(name="Basic info", value=f"Team: {team_name}\n"
                                                f"Cost: £{(player_dict['now_cost']/10):.1f} million", inline=False)

        if player_dict["news"] != "":
            self.add_field(name="News:", value=player_dict["news"], inline=False)

        self.add_field(name="Performance", value=f"Form: {player_dict['form']}\n"
                                                 f"Total Points: {player_dict['total_points']}\n"
                                                 f"Points per Match: {player_dict['points_per_game']}\n"
                                                 f"Form Value: {player_dict['value_form']}\n"
                                                 f"Value For Season: {player_dict['value_season']}", inline=True)

        self.add_field(name="Popularity",
                       value=f"Selected by: {player_gameweek_info['selected']}"
                            f" ({player_dict['selected_by_percent']}%)\n"
                             f"Transfers in this gameweek: {player_gameweek_info['transfers_in']}\n"
                             f"Transfers out this gameweek: {player_gameweek_info['transfers_out']}\n"
                             f"Net transfers this gameweek: "
                             f"{transfer_balance_emojifier(player_gameweek_info['transfers_balance'])}", inline=True)


        if player_gameweek_info["was_home"]:
            home_team = {'name': team_name}
            # Away team is opposing team if player is at home. Team ids are shifted by 1
            away_team = fplApi.view_team(player_gameweek_info["opponent_team"] - 1)
        else:
            home_team = fplApi.view_team(player_gameweek_info["opponent_team"] - 1)
            away_team = {'name': team_name}

        self.add_field(name=f"Gameweek {str(gameweek)} performance:",
                       value=f"{home_team['name']} {str(player_gameweek_info['team_h_score'])} - "
                             f"{str(player_gameweek_info['team_a_score'])} {away_team['name']}",
                       inline=False)