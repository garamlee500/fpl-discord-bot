import requests
import json
import asyncio
from typing import Union

GAMEWEEK_COUNT = 38


def get_player_image(image_link: str) -> str:
    """
    Get the full image link of player, using given image link in api
    :param image_link: Image link found in json
    :return: Full image link to player
    """
    return "https://resources.premierleague.com/premierleague/photos/players/110x140/p" + image_link


def extract_dictionary(dictionary: dict, keys_to_extract: list) -> dict:
    """
    Uses dictionary comprehension to keep only certain keys from the dictionary
    :param dictionary:
    :param keys_to_extract:
    :return:
    """
    return {key: dictionary[key] for key in keys_to_extract}


class FplApi:
    """
    FplApi aims to creates a simple way to interact with fpl's api endpoints

    Note:
        api/entry/{team-id}/history/ endpoint not implemented,
        as with all authentication requiring endpoints.
    """

    def __init__(self):
        """
        Initialises new FplApi.
        All updates done here too
        """
        self.main_data = {}
        self.fixtures = {}
        self.current_gameweek_data = {}
        self.playername_id_dict = {}
        self.team_list = []
        self.player_list = []
        self.gameweek = 0

        self.update_all()

    def access_fpl_api(self, endpoint: str) -> dict:
        """
        Access the fpl api, using an endpoint, attached to:
        https://fantasy.premierleague.com/api/


        :param endpoint: endpoint to be attached to api link
        :return: Returns response, unpacked as a dictionary
        """

        api_data = requests.get("https://fantasy.premierleague.com/api" + endpoint)
        unpacked_data = json.loads(api_data.content)
        return unpacked_data

    def get_fpl_league(self, league_id: int) -> dict:
        """
        Get access to data about a fpl league
        Data in here includes:
            League Standings
            Basic League Data
            Scoring
        :param league_id: Id of fpl league to get
        :return: Fpl league, in form of dictionary
        """

        fpl_league = self.access_fpl_api(f"/leagues-classic/{league_id}/standings/")
        return fpl_league

    def get_fpl_manager(self, manager_id: int) -> dict:
        """
        Get basic data about fpl managers
        Data in here includes:
            Basic Player Details
            Fpl League Standings
            Fpl Financial info
        :param manager_id: Id of fpl manager
        :return: Dictionary containing fpl data
        """
        fpl_manager_data = self.access_fpl_api(f"/entry/{str(manager_id)}/")
        return fpl_manager_data

    def get_fpl_team(self, manager_id: int, gameweek: int = 0) -> dict:
        """
        Get access to data about a fpl manager's team
        Data in here includes:
            Team Selection
            Chip Usage
            Live Points
            Live Rank
            Substitution Information
            Squad Value
        :param manager_id: Id of fpl manager to view team of
        :param gameweek: Gameweek to look at team for
        :return:  Fpl team, in form of dictionary
        """

        # If no gameweek is selected, presume gameweek is current gameweek
        if gameweek == 0:
            gameweek = self.gameweek

        fpl_team = self.access_fpl_api(f"/entry/{manager_id}/event/{gameweek}/picks/")
        return fpl_team

    def get_fpl_transfers(self, manager_id: int) -> dict:
        """
        Get access to data about a fpl managers' transfer info
        Data in here includes:
            Transfers
            Transfer costs
            Transfer dates
            Transfer Gameweek
        :param manager_id:
        :return:
        """
        fpl_transfers = self.access_fpl_api(f"/entry/{str(manager_id)}/transfers/")
        return fpl_transfers

    def get_gameweek_player_data(self, gameweek: int) -> dict:
        """
        Gets data about a certain gameweek
        Data in here includes:
            Detailed Players' stats
            Players' fpl point breakdown
        :param gameweek: Gameweek to fetch
        :return: Current gameweek data
        """
        gw_data = self.access_fpl_api(f"/event/{str(gameweek)}/live/")
        return gw_data

    def get_player_history(self, player_id: int) -> dict:
        """
        Gets specific player data
        Data in here includes:
            Players' fixtures/results
            Players' game-specific stats + fpl points
            Previous season stats
        :param player_id: The id of the player
        :return: Statistics dictionary for that player
        """

        player_data = self.access_fpl_api(f"/element-summary/{str(player_id)}/")
        return player_data

    def update_all(self):
        self.update_main_data()
        self.update_current_gameweek()
        self.update_fixtures()
        self.update_current_gameweek_data()
        self.update_team_list()
        self.update_player_list()
        self.update_playername_id_dict()

    def update_current_gameweek(self) -> int:
        """
        Goes through the gameweek list to try and find current gameweek

        :return: Current Gameweek
        """
        # Go through all gameweeks
        for i in range(GAMEWEEK_COUNT):
            # Keep going through gameweeks until the current one is found
            if self.main_data["events"][i]["is_current"]:
                # Return current gameweek
                self.gameweek = i + 1
                return self.gameweek

        # Not sure how if there's no current gameweek? (I'm not sure how the api works yet so i'll leave this here)
        # If there's no current use the previous one
        for i in range(GAMEWEEK_COUNT):
            # Keep going through gameweeks until the previous one is found
            if self.main_data["events"][i]["is_previous"]:
                # Return current gameweek
                self.gameweek = i + 1
                return self.gameweek

        # If all gameweeks finished, return gameweek 38
        self.gameweek = GAMEWEEK_COUNT
        return self.gameweek

    def update_current_gameweek_data(self):
        """
        Does get_gameweek_player_data for the current gameweek
        :return: None
        """
        self.current_gameweek_data = self.get_gameweek_player_data(self.gameweek)

    def update_fixtures(self):
        """
        Updates fixture/result list of data
        Data in here includes:
            fixtures
            results
            FDR
            Game stats
        """

        # Fetch api data, convert it to dictionary using, and store it
        self.fixtures = self.access_fpl_api("/fixtures/")

    def update_main_data(self):
        """
        Updates the main backbone of the data
        Data in here includes:
            simple_player_stats
            team_stats
            gameweek_stats
        """

        # Fetch api data, convert it to dictionary using, and store it
        self.main_data = self.access_fpl_api("/bootstrap-static/")

    def update_player_list(self) -> list:
        """
        Update the list of players, returning the list too
        This data includes:
            Player Names
            Player Injury Status
            Player
            Most General Statstics
        :return:
        """
        self.player_list = self.main_data["elements"]
        return self.player_list

    def update_playername_id_dict(self) -> dict:
        """
        Creates and updates a dictionary that maps all player ids to their last name
        :return: Returns the dictionary
        """

        self.playername_id_dict = {player["id"]: player["web_name"] for player in
                                   self.player_list}

        return self.playername_id_dict

    def update_team_list(self) -> list:
        """
        Update the list of teams, returning the list too
        This data includes:
            Team Names
            Team Home/Away/Defence/Attack Strength
        :return:
        """
        self.team_list = self.main_data["teams"]
        return self.team_list

    def view_match(self, fixture_id: int) -> dict:

        for fixture in self.fixtures:
            if fixture["id"] == fixture_id:
                return fixture

        return {}

    def view_player(self, player_id: int, matches: bool = False) -> dict:
        """
        View a players' stats
        This data includes:
            Fixtures
            Results
            Detailed match stats
            Detailed overall stats
        :param player_id: Id of player - this is the fpl mandated id
        :param matches: To include match history or not
        :return:
        """

        player_profile = {}

        player_matches = self.get_player_history(player_id)
        for player in self.player_list:
            if player["id"] == player_id:
                player_profile = player

        player_profile_info_wanted = ["first_name",
                                      "second_name",
                                      "web_name",
                                      "photo",
                                      "chance_of_playing_this_round",
                                      "chance_of_playing_next_round",
                                      "cost_change_event",
                                      "cost_change_start",
                                      "now_cost",
                                      "dreamteam_count",
                                      "event_points",
                                      "points_per_game",
                                      "form",
                                      "selected_by_percent",
                                      "team",
                                      "total_points",
                                      "transfers_in_event",
                                      "transfers_out_event",
                                      "value_form",
                                      "value_season",
                                      "minutes",
                                      "goals_scored",
                                      "assists",
                                      "clean_sheets",
                                      "goals_conceded",
                                      "own_goals",
                                      "penalties_saved",
                                      "penalties_missed",
                                      "yellow_cards",
                                      "red_cards",
                                      "saves",
                                      "bonus",
                                      "bps",
                                      "influence",
                                      "creativity",
                                      "threat",
                                      "corners_and_indirect_freekicks_order",
                                      "corners_and_indirect_freekicks_text",
                                      "direct_freekicks_order",
                                      "direct_freekicks_text",
                                      "penalties_order",
                                      "penalties_text",
                                      "id",
                                      "news"]

        player_profile = extract_dictionary(player_profile, player_profile_info_wanted)

        first_gameweek = player_matches["history"][0]["round"]
        full_name = player_profile["first_name"] + " " + player_profile["second_name"]

        player_profile = player_profile | {'first_gameweek': first_gameweek,
                                           'full_name': full_name}
        if matches:
            # Union the two dictionaries and return (PYTHON 3.9+)!!!
            return player_profile | player_matches
        else:
            return player_profile

    def view_player_gameweek_points(self, player_id: int, gameweek: int = 0) -> dict:
        """
        View the points breakdown of a player on a certain gameweek
        :param player_id: Id of player
        :param gameweek: Gameweek to view player's point breakdown on
        :return: Points breakdown
        """
        if gameweek == 0:
            gameweek = self.gameweek

        gameweek_data = self.get_gameweek_player_data(gameweek)

        for player in gameweek_data["elements"]:
            if player_id == player["id"]:
                return player["explain"][0]["stats"]
        return {}

    def view_player_on_gameweek(self, player_id: int, gameweek: int = 0):
        """
        View a players' stats on a certain gameweek (note this won't work for fixtures)
        Data includes:
            Selected count
            General Match stats
            Results
            FPL Match Stats
        :param player_id: Id of player to search
        :param gameweek: Gameweek to view history
        :return: Data for player on gameweek
        """
        if gameweek == 0:
            gameweek = self.gameweek

        player_matches = self.get_player_history(player_id)["history"]

        for match in player_matches:
            if match["round"] == gameweek:
                return match

        return None

    def view_team(self, team: Union[int, str]) -> dict:
        """
        View basic team info, in processed dictionary
        :param team: Name or list position of team
        :return: Team info, as dictionary
        """

        team_selected = {}

        # If team is given as an id, find team list item corresponding
        # to that list position. This uses default python list
        # position numbers, not the one on the fpl api starting
        # from 1
        if isinstance(team, int):
            team_selected = self.team_list[team]

        # If team is given as a name, go through list of teams
        # Until one with the same name is found
        elif isinstance(team, str):
            for team_item in self.team_list:
                if team_item["name"] == team:
                    team_selected = team_item

        else:
            return {}

        # Keys of info we want from team
        team_info_wanted = ["name",
                            "strength",
                            "strength_overall_home",
                            "strength_overall_away",
                            "strength_attack_home",
                            "strength_attack_away",
                            "strength_defence_home",
                            "strength_defence_away"]

        # Dictionary Comprehension goes through team and finds info wanted
        team_info = extract_dictionary(team_selected, team_info_wanted)
        return team_info

    def view_teamname_list(self) -> list:
        """
        Get the list of team names in premier league
        :return: List of team names
        """
        teamname_list = []
        for team in self.team_list:
            teamname_list.append(team["name"])

        return teamname_list

    def view_team_logo(self, team_id: int) -> str:
        """
        Find the link to a team's logo.
        :param team_id: Id of team (in teamlist, not api)
        :return: Url linking to team logo
        """

        team = self.team_list[team_id]
        team_code = str(team["code"])
        team_logo_url = f"https://resources.premierleague.com/premierleague/badges/100/t{team_code}.png"

        return team_logo_url

    async def regular_updater(self, update_interval: int = 60):
        """
        Refresh data every fixed interval, to keep data updated.
        Defaults to one minute.
        :param update_interval: Number of seconds to wait before updating
        """
        while True:
            await asyncio.sleep(update_interval)
            self.update_all()
