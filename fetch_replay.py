import os
import requests

default_desitnation_folder = 'replays'
default_game = "age2"               #Could be potentially used for oter titles. Currently only tested with age2.

'''
Example headers and payload for fetching match details.
These were captured using Fiddler Everywhere while using the Age of Empires website.
'''
default_headers = {
 'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
 'accept':'application/json, text/javascript, */*; q=0.01',
 'accept-language':'en-US,en;q=0.9',
 'accept-encoding':'gzip, deflate, br, zstd',
 'content-type':'application/json',
 'content-length':'58',
 'origin':'https://www.ageofempires.com',
 'dnt':'1',
 'sec-gpc':'1',
 'referer':'https://www.ageofempires.com/',
 'sec-fetch-dest':'empty',
 'sec-fetch-mode':'cors',
 'sec-fetch-site':'same-site',
 'te':'trailers',
#Appears to work without cookies, but including them to match the captured request.
#'cookie':'MSCC=cid=7ztop15tvhqdnrdzi8yiujxo-c1=2-c2=2-c3=2; age-user=true; age_login_expire=1'
}

endpoints = {
    "match_details": "GetMatchDetail",
    "player_stats": "GetFullStats",
    "player_match_list": "GetMatchList",
    "player_campaign_stats": "GetCampaignStats"
}

# leaderboard https://api.ageofempires.com/api/v2/ageii/Leaderboard

def get_replay_url(match_id, profile_id = 1):
    '''
    Constructs the URL to fetch the replay file for a given match ID and profile ID.
    Profile ID can be anything, as long as somthing is included. Default=1.
    '''
    url = f'https://api.ageofempires.com/api/GameStats/AgeII/GetMatchReplay/?matchId={match_id}&profileId={profile_id}'
    return url

def fetch_replay(match_id, profile_id = 1, destination_folder=default_desitnation_folder):
    '''
    Fetches the replay file for a given match ID and profile ID.
    Profile ID can be anything, as long as somthing is included. Default=1.
    Saves the replay file as a zip in the desitnation_folder.
    '''
    url = get_replay_url(match_id, profile_id)
    print(f"Fetching replay from URL: {url}")
    # Download the file from the URL
    response = requests.get(url)
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        #Create directory if it doesn't exist
        os.makedirs(destination_folder, exist_ok=True)
        # Save the file to the destination folder
        file_name = f'{destination_folder}/{match_id}.zip'
        with open(file_name, 'wb') as f:
            f.write(response.content)
        print(f"File '{file_name}' downloaded successfully!")
    else:
        print(f"Failed to download file. Status code: {response.status_code}")
    
    return response.status_code

def fetch_player_match_list(profile_id, game=default_game, sortColumn="dateTime", sort_direction="DESC", match_type="3"):
    '''
    Fetches the match list for a given profile ID. Only the 10 most recent matches are returned.
    Additional parameters can be set to modify the results.
    '''

    #Full payload example for fetching player match list, captured using Fiddler Everywhere:
    #{"gamertag":"unknown user","playerNumber":0,"undefined":null,"game":"age2","profileId":199325,"sortColumn":"dateTime","sortDirection":"DESC","page":1,"recordCount":10,"matchType":"3"}

    #Only profileId, game, sortColumn, sortDirection, and matchType appear to be required. The rest have no effect.
    #   * (Setting "page" as anything other than 1 appears to return an empty list.)
    #   * It is unclear if setting "game" to anything other than AOE2 will have any effect. (ie. AOE1)
    #   * sortColumn can be dateTime, wins, or civilization
    #   * sortDirection can be ASC or DESC
    #TODO: Investigate matchType values further. 
    # 1:  Deathmatch
    # 2:  Team Deathmatch
    # 3:  1v1 RandomMap
    # 4:  Team RandomMap
    # 13: Empire Wars
    # 14: Team Empire Wars
    # 25: Return of Rome
    # 26: ??Team Return of Rome **Unconfirmed
    # 29: RedBull Wololo: Londinium

    payload = f'{{"game":"{game}","profileId":"{profile_id}","sortColumn":"{sortColumn}", "sortDirection":"{sort_direction}","matchType":"{match_type}"}}'
    response = fetch_stats("player_match_list", profile_id=profile_id, payload=payload)    
    return response

def fetch_stats(endpoint, match_id=1, profile_id=1, headers=default_headers, payload=None):
    '''
    Fetches the match details for a given match ID and profile ID.
    Profile ID of one of the human players must be included.
    '''
    #Default payload
    if not payload:
        payload = f'{{"matchId":"{match_id}","game":"age2","profileId":"{profile_id}"}}'
    
    #Fetch the stats from the API
    response = requests.request("POST", f"https://api.ageofempires.com/api/GameStats/AgeII/{endpoints[endpoint]}", headers=headers, data=payload)
    
    return response

def main():
    match_id = 45255542
    profile_id = 271202
    # status_code = fetch_replay(match_id, 1)
 
    # match_details = fetch_stats("match_details", match_id, profile_id)
    # full_stats = fetch_stats("player_stats", match_id, profile_id)
    player_match_list = fetch_player_match_list(profile_id, match_type="3")

    # print(f"Match Details Response: {match_details.status_code} {match_details.content}\n")
    # print(f"Full Stats Response: {full_stats.status_code} {full_stats.content}\n")
    print(f"Player Match List Response: {player_match_list.status_code} {player_match_list.content}\n")

if  __name__ == "__main__":
    main()