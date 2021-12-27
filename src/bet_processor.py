from typing import Union

from bot import fplApi, fplDatabase


def odd_finder(bet_type: str, round_it: bool = True) -> float:
    '''
    Finds the average number of times a certain bet is made
    for one correct bet (the reciprocal of the chance for a certain bet to be correct)
    :param bet_type: Name of the type of bet
    :param round_it: Whether to round the number to a whole number. Also rounds everything smaller than 2 up to 2.
    :return: The average number of times a certain bet is made. If no bets made of type, 0 is returned
    '''
    bets = fplDatabase.find_all_finished_bets(bet_type=bet_type)

    correct_total = 0

    for bet in bets:
        # Check if correct
        if bet[7] == 1:
            correct_total += 1

    if correct_total == 0:
        return 0

    odd = len(bets) / correct_total
    if round_it:
        odd = round(odd)
        if odd < 2:
            odd = 2

    return odd


def is_bet_correct(bet_condition: str, bet_type: str) -> bool:
    bet_checker_functions = {
        'match_score': match_score_checker,
        'match_winner': match_winner_checker
    }
    return bet_checker_functions[bet_type](bet_condition)


def bet_info(bet_condition: str, bet_type: str) -> str:
    bet_stringerfier_functions = {
        'match_score': match_score_details,
        'match_winner': match_winner_checker
    }
    return bet_stringerfier_functions[bet_type](bet_condition)


def match_score_details(bet_condition: str) -> str:
    parsed_bet = bet_condition.split(',')
    match = fplApi.view_match(int(parsed_bet[0]))
    predicted_home_score = min(int(parsed_bet[1]), 10)
    predicted_away_score = min(int(parsed_bet[2]), 10)

    home_team = fplApi.view_team(match['team_h'] - 1)['name']
    away_team = fplApi.view_team(match['team_a'] - 1)['name']
    return f'{home_team} {predicted_home_score} - {predicted_away_score} {away_team}'

def match_winner_details(bet_condition: str) -> str:
    parsed_bet = bet_condition.split(',')
    match = fplApi.view_match(int(parsed_bet[0]))

    home_team = fplApi.view_team(match['team_h'] - 1)['name']
    away_team = fplApi.view_team(match['team_a'] - 1)['name']

    if int(parsed_bet[1]) == 0:
        return f'{home_team} to beat {away_team}'
    elif int(parsed_bet[1]) == 2:
        return f'{away_team} to beat {home_team}'
    else:
        return f'{home_team} and {away_team} to draw'

def match_score_checker(bet_condition: str) -> Union[bool, None]:
    """
    Checks whether the score prediction for a match was correct
    :param bet_condition: Predicted score. Should be given as a string, in form '<match_id>,<home_score>,<away_score>'
    :return: True for correct, False for incorrect, and None for uncheckable
    """
    parsed_bet = bet_condition.split(',')
    if len(parsed_bet) != 3:
        return None
    try:
        match = fplApi.view_match(int(parsed_bet[0]))
        predicted_home_score = min(int(parsed_bet[1]), 10)
        predicted_away_score = min(int(parsed_bet[2]), 10)
    except ValueError:
        return None

    if not match['finished']:
        return None

    if min(match['team_h_score'], 10) == predicted_home_score and min(match['team_a_score'],
                                                                      10) == predicted_away_score:
        return True
    else:
        return False


def match_winner_checker(bet_condition: str) -> Union[bool, None]:
    """
    Checks whether the user predicted the winner of the match correctly

    :param bet_condition: Predicted result. Should be given as a string in the form '<match_id>,<0/1/2>'
                          Where 0 is a home win, 1 is a draw, and 2 is an away win
    :return: True for correct, False for incorrect, and None for uncheckable
    """
    parsed_bet = bet_condition.split(',')
    if len(parsed_bet) != 2:
        return None

    match = fplApi.view_match(int(parsed_bet[0]))

    if not match['finished']:
        return None

    if match['team_h_score'] > match['team_a_score']:
        winner = 0
    elif match['team_h_score'] < match['team_a_score']:
        winner = 2
    else:
        winner = 1

    if winner == int(parsed_bet[1]):
        return True
    else:
        return False
