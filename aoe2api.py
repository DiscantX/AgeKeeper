import os
import requests
import json
import zipfile
import errno
from string import Template
from urllib.parse import urlparse, parse_qs

'''
Default configuration values.
These can be modified as needed.
'''
defaults = {
    "destination_folder": "replays",       #Folder where replay files will be saved. Can be changed to any valid path.
    "game": "age2",                        #The Age of {x} title to use. Could be potentially used for other titles. Currently only tested with age2.
    "profile_id": 199325,                  #Player's profile id. Default = Hera's profile ID, used for testing. Can be replaced with any profile ID.
    "match_id": 453704442,                 #A played match's id. Default = A match ID from Hera's profile, used for testing. Can be replaced with any match ID.
    "unzip": True,                         #Whether to unzip downloaded replay files.
    "remove_zip": True,                    #Whether to remove the original zip file after unzipping.
    "headers": {                           #Headers to include in API requests. These were captured from a request made on the official Age of Empires website, and may not be necessary for successful requests. Modify as needed.
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
        # Appears to work without cookies, but they are included here to match the captured request.
        # If you have valid cookies from the official website, you can include them here.
        # Don't use this exact value, as you will not have the same cookies as the original request.

        #'cookie':'MSCC=cid=7ztop15tvhqdnrdzi8yiujxo-c1=2-c2=2-c3=2; age-user=true; age_login_expire=1'
    }
}

endpoints = {
    "replay":
                    {
                    "endpoint": "https://api.ageofempires.com/api/GameStats/AgeII/GetMatchReplay/?matchId=$matchId&profileId=$profileId",
                    "method": "GET"
                    },
    "match_details": 
                    {
                    "endpoint": "https://api.ageofempires.com/api/GameStats/AgeII/GetMatchDetail",
                    "method": "POST"
                    },
    "player_stats": {
                    "endpoint": "https://api.ageofempires.com/api/GameStats/AgeII/GetFullStats",
                    "method": "POST"
                    },
    "player_match_list":
                    {
                    "endpoint": "https://api.ageofempires.com/api/GameStats/AgeII/GetMatchList",
                    "method": "POST"
                    },
    "player_campaign_stats": 
                    {
                    "endpoint": "https://api.ageofempires.com/api/GameStats/AgeII/GetCampaignStats",
                    "method": "POST"
                    },
    "leaderboard":
                    {
                    "endpoint": "https://api.ageofempires.com/api/v2/ageii/Leaderboard",
                    "method": "POST"
                    },
}

def save_replay(response, destination_folder=defaults["destination_folder"], unzip=defaults["unzip"], remove_zip=defaults["remove_zip"]):
    '''
    Saves a replay file from a GET request response to the destination folder specified in defaults.
    The file is saved in the specified destination folder as {match_id}.zip.
    
    Note: When making the GET request, both matchId and profileId must be included in the URL query parameters,
    though the actual value of profileId does not matter.
    '''
    #Retrieve the match ID from the request URL query parameters, required for file naming
    match_id = parse_qs(urlparse(response["request"].url).query)["matchId"][0]
    if response["status_code"] == 200:
        destination_path = f"{destination_folder}/{match_id}.zip"
        #Create directory if it doesn't exist
        os.makedirs(destination_folder, exist_ok=True)
        try:
            # raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC), destination_path)  #Used for testing. Can be remmoved in prod.

            # Save the file to the destination path
            file_name = destination_path
            with open(file_name, 'wb') as f:
                f.write(response["content"])
            print(f" * File '{file_name}' saved successfully.")
            if unzip:
                with zipfile.ZipFile(file_name, 'r') as zip_ref:
                    zip_ref.extractall(destination_folder)
                    print(f"' - {file_name}' unzipped successfully. ", end="")
                    if remove_zip:
                        if os.path.exists(destination_path):
                            os.remove(destination_path)
                            print(f" * Removed zip file '{destination_path}' after extraction.")
                        else:
                            print(f" * Failed to remove zip file. The file '{destination_path}' does not exist")
                    else:
                        print()  # Add a newline after extraction message, so it doesn't flow into the next print.

        except OSError as e:
            response["status_code"] = e.errno
            response["message"] = e.strerror
            print(f" ! Caught an operating system error wile saving replay: Error {response['status_code']}: {response['message']}")

    else:
        print(f" ! Failed to save file. Status code: {response['status_code']} {response['message']}")
    
    return response["status_code"]

def fetch_player_match_list(profile_id, game=defaults["game"], sortColumn="dateTime", sort_direction="DESC", match_type="3"):
    '''
    Fetches the match list for a given profile ID. Only the 10 most recent matches are returned.
    Additional parameters can be set to modify the results.
    '''

    #Full payload example for fetching player match list, captured using Fiddler Everywhere:
    #{"gamertag":"unknown user","playerNumber":0,"undefined":null,"game":"age2","profileId":199325,"sortColumn":"dateTime","sortDirection":"DESC","page":1,"recordCount":10,"matchType":"3"}

    #Only profileId, game, sortColumn, sortDirection, and matchType appear to be required. The rest have no effect.
    #   * (Setting "page" as anything other than 1 appears to return an empty list.)
    #   * It is unclear if setting "game" to anything other than age2 will have any effect. (ie. age1, age3, age4, aom)
    #   * sortColumn value can be dateTime, wins, or civilization
    #   * sortDirection value can be ASC or DESC
    #   * Known matchType values: 
    #       1:  Deathmatch
    #       2:  Team Deathmatch
    #       3:  1v1 RandomMap
    #       4:  Team RandomMap
    #       13: Empire Wars
    #       14: Team Empire Wars
    #       25: Return of Rome
    #       26: ??Team Return of Rome **Unconfirmed
    #       29: RedBull Wololo: Londinium
    #     TODO: Investigate matchType values further.

    payload = f'{{"game":"{game}","profileId":"{profile_id}","sortColumn":"{sortColumn}", "sortDirection":"{sort_direction}","matchType":"{match_type}"}}'
    response = fetch_endpoint("player_match_list", profile_id=profile_id, data=payload)    
    return response

def fetch_leaderboard(region="7", match_type="3", console_match_type=15, search_player="", page=1, count=100, sort_column="rank", sort_direction="ASC"):
    '''
    Fetches the leaderboard by region and matchtype. Returns the top 100 players per page. Can also be used for player search by name.
    '''
    payload = f'{{"region":"{region}","matchType":"{match_type}","consoleMatchType":{console_match_type},"searchPlayer":"{search_player}","page":{page},"count":{count},"sortColumn":"{sort_column}","sortDirection":"{sort_direction}"}}'
    response = fetch_endpoint("leaderboard", data=payload)
    return response

def fetch_endpoint(endpoint_name=None, profile_id=defaults["profile_id"], match_id=defaults["match_id"], headers=defaults["headers"], data=None):
    '''
    Fetches various stats from the Age of Empires API. Endpoint name must be specified.

    In the case of a GET request, data will contain the values to be passed in the URL.
    In the case of a POST request, data will contain the payload to be sent in the body of the request,
    which must be in the format of a valid JSON string.
    If no data is provided, default values will be used for the url/payload.  
    If profile_id and match_id are included, they will be used to construct the default payload/url.
    '''

    #Validate the endpoint
    if not endpoint_name or endpoint_name not in endpoints:
        return {"status_code": 400, "message": f"Invalid or missing endpoint. Valid endpoints are: {list(endpoints.keys())}", "content": None}

    #Default payload
    if not data:
        data= f'{{"matchId":"{match_id}", "profileId":"{profile_id}"}}'
    
    #Fetch the stats from the API
    print(f"Fetching stats from endpoint: '{endpoint_name}' with data: {data}")
    variables = {}

    if endpoints[endpoint_name]["method"] == "GET":
        values = json.loads(data)
        final_endpoint = Template(endpoints[endpoint_name]["endpoint"]).substitute(**values)
        response = requests.request("GET", final_endpoint)
    elif endpoints[endpoint_name]["method"] == "POST":
        response = requests.request("POST", f"{endpoints[endpoint_name]['endpoint']}", headers=headers, data=data)
    else:
        return {"status_code": 400, "request": response.request, "message": f"Invalid method for endpoint {endpoint_name}", "content": None}
    
    return {"status_code": response.status_code, "request": response.request, "message": response.reason, "content": response.content}

def run_endpoint_tests():
    match_id = defaults["match_id"] 
    profile_id = defaults["profile_id"]

    replay = fetch_endpoint("replay", match_id=match_id)
    save_replay(replay, unzip=False, remove_zip=False)
    match_details = fetch_endpoint("match_details", profile_id, match_id)
    full_stats = fetch_endpoint("player_stats", profile_id, match_id)
    player_match_list = fetch_player_match_list(profile_id, match_type="3")
    campaign_stats = fetch_endpoint("player_campaign_stats", profile_id)
    leaderboard = fetch_leaderboard()

    print(f"Replay Download Response  : {replay['status_code']} {replay['message']}\tContent Size: {len(replay['content'])} B\n")
    print(f"Match Details Response: {match_details['status_code']} {match_details['message']} \nContents:\n {match_details['content']}\n")
    print(f"Full Stats Response: {full_stats['status_code']} {full_stats['message']} \nContents:\n {full_stats['content']}\n")
    print(f"Player Match List Response: {player_match_list['status_code']} {player_match_list['message']} \nContents:\n {player_match_list['content']}\n")
    print(f"Campaign Stats Response: {campaign_stats['status_code']}  {campaign_stats['message']} \nContents:\n {campaign_stats['content']}\n")
    print(f"Leaderboard Response: {leaderboard['status_code']}  {leaderboard['message']} \nContents:\n {leaderboard['content']}\n")

def main():
    run_endpoint_tests()

if  __name__ == "__main__":
    main()