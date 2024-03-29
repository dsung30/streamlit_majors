import streamlit as st
import pandas as pd
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import re

DRAFT_RESULTS_URL = ('https://raw.githubusercontent.com/dsung30/streamlit_majors/main/draft_results.csv')

# 2023 PGA CHAMPIONSHIP
ESPN_URL = ('https://www.espn.com/golf/leaderboard/_/tournamentId/401465539')
PAR = 71

def get_cutline(header, body):
    cutline = 1000
    cutline_regex = "[\+|\-]?\d+"
    rows = body.find_all('tr')
    tot_players = len(rows)
    col_names = header.find_all('th')
    col_dict = {}
    for i in range(len(col_names)-1):
        if len(col_names[i].get_text()):
            col_dict[col_names[i].get_text()] = i

    for i in range(tot_players):
        row = rows[i]
        td = row.find_all('td')
        if len(td) == 1:
            status = td[0].get_text()
            if "Projected Cut" in status:
                continue
            else:
                r = re.search(cutline_regex, status)
                cutline = int(r.group(0))
        else:
            continue
    return cutline

def get_constants():
    constants = pd.read_csv(ESPN_CONSTANTS_URL)
    url = constants.iloc[0].value
    folder = constants.iloc[1].value
    par = int(constants.iloc[2].value)
    cutline = int(constants.iloc[3].value)
    return url, folder, par, cutline

def get_leaderboard(url):
    result = requests.get(ESPN_URL)
    soup = BeautifulSoup(result.text, "html.parser")
    bodies = soup.find_all(class_="Table__TBODY")
    body = bodies[len(bodies)-1]
    headers = soup.find_all(class_="Table__THEAD")
    header = headers[len(headers)-1]
    return header, body

def get_draft_results():
    draft_results = pd.read_csv(DRAFT_RESULTS_URL)
    return draft_results

def calc_score(draft_results, cutline, par, header, body):
    player_dict = draft_results.set_index('player_name').to_dict()['owner']
    owners = np.array(draft_results['owner'])
    owner_standings = dict.fromkeys(np.unique(owners))
    rows = body.find_all('tr')
    tot_players = len(rows)
    col_names = header.find_all('th')
    col_dict = {}
    for i in range(len(col_names)-1):
        if len(col_names[i].get_text()):
            col_dict[col_names[i].get_text()] = i
    
    full_standings = pd.DataFrame(columns=['pos', 'player', 'owner', 'score', 'thru', 'today', 'adj_score', 'status'])

    for k in owner_standings.keys():
        owner_standings[k] = 0

    for i in range(tot_players):
        row = rows[i]
        td = row.find_all('td')
        if len(td) == 1:
            pos = '----'
            player_name = '-----------------'
            status = td[0].get_text()
            owner = '-----'
            today = '--'
            thru = '--'
            score = '---'
            adj_score = '---'
            new_row = pd.DataFrame({'pos': pos, 'player': player_name, 'owner': owner, 'score': score, 'thru': thru, 'today': today, 'adj_score':adj_score, 'status': status}, index = [0])
            full_standings = pd.concat([full_standings, new_row]).reset_index(drop=True)
        else:
            player_name = td[col_dict['PLAYER']].get_text()
            if player_name in player_dict.keys():
                owner = player_dict[player_name]
                pos = td[col_dict['POS']].get_text()
                score = td[col_dict['SCORE']].get_text()
                if score in ['CUT', 'WD']:
                    r1 = int(td[col_dict['R1']].get_text())
                    r2 = int(td[col_dict['R2']].get_text())
                    adj_score = r1 + r2 - 2 * par
                    status = 'CUT'
                    score = "+" + str(adj_score) if adj_score > 0 else adj_score
                elif score == 'DQ':
                    adj_score = 0
                    status = 'DQ'
                    score = 'DQ'
                else:
                    print(player_name)
                    score_int = int(re.sub('[+]', '', score)) if score != "E" else 0
                    adj_score = min(score_int, cutline)
                    status = ''
                owner_standings[owner] = owner_standings[owner] + adj_score
                try:
                    today = td[col_dict['TODAY']].get_text()
                    thru = td[col_dict['THRU']].get_text()
                except KeyError:
                    today = ""
                    thru = "F"

                adj_score = "+" + str(adj_score) if adj_score > 0 else "E" if adj_score == 0 else adj_score
                new_row = pd.DataFrame({'pos': pos, 'player': player_name, 'owner': owner, 'score': score, 'thru': thru, 'today': today, 'adj_score':adj_score, 'status': status}, index = [0])
                full_standings = pd.concat([full_standings, new_row]).reset_index(drop=True)
            else:
                continue
    owner_standings_df = pd.DataFrame(list(owner_standings.items()))
    owner_standings_df.columns = ['owner', 'total']
    owner_standings_df = owner_standings_df.sort_values(by = 'total', ascending = True)
    owner_standings_df.index = list(range(1, len(owner_standings_df)+1))
    owner_standings_df.style.format({'total': '{:+g}'})
    print(owner_standings_df)
    return full_standings, owner_standings_df

def main():
    header,body = get_leaderboard(ESPN_URL)
    draft_results = get_draft_results()
    cutline = get_cutline(header, body)
    full_standings,owner_standings = calc_score(draft_results,cutline, PAR, header,body)
    st.subheader("Full Standings")
    st.table(data=full_standings)
    st.subheader("Team Standings")
    st.table(data=owner_standings)

if __name__ == '__main__':
    main()
