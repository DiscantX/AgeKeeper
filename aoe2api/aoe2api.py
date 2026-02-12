import os
import requests
import json
import zipfile
import errno
import argparse
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
    "unzip": False,                         #Whether to unzip downloaded replay files.
    "remove_zip": False,                    #Whether to remove the original zip file after unzipping.
    "match_type": 3,
    
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

'''
API endpoints for fetching replays and stats. The keys are used to identify the endpoint when calling fetch_endpoint().
The endpoint URLs and methods were captured from requests made on the official Age of Empires website, and may be subject to change if the website is updated.
'''
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
    "global_stats":
                    {
                    "endpoint": "https://api.ageofempires.com/api/v2/ageii/GetGlobalStats",
                    "method": "POST"
                    }
}


## <------------------------------------- Replay functions -------------------------------------> ##                       

def save_replay(
    response,
    destination_folder=defaults["destination_folder"],
    unzip=defaults["unzip"],
    remove_zip=defaults["remove_zip"],
    quiet=False,
    match_id=None,
):
    '''
    Saves a replay file from a GET request response to the destination folder as {match_id}.zip.
    Use in conjunction with fetch_replay() to download and save a replay file. Alternatively, use download_replay() to do both in one step.
    Can optionaly unzip the replay file and remove the original zip after extraction.

    :param response: The response from a GET request to the replay endpoint. Should be in the format of the return value of fetch_replay().
    :param destination_folder: The folder where the replay file will be saved. Default is "replays".
    :param unzip: Whether to unzip the replay file after downloading. Default is False. Unzipped files will be saved in the same destination folder.
    :param remove_zip: Whether to remove the original zip file after unzipping. Default is False. Removing the zip without unzipping first will result in loss of the replay file, so use with caution.
    '''
    if match_id is None:
        request = response.get("request")
        if request is None:
            response["status_code"] = 400
            response["message"] = "Missing request info; pass match_id to save_replay()."
            if not quiet:
                print(f" ! Failed to save file. Status code: {response['status_code']} {response['message']}")
            return response
        #Retrieve the match ID from the request URL query parameters, required for file naming
        match_id = parse_qs(urlparse(request.url).query)["matchId"][0]
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
            if not quiet:
                print(f" * File '{file_name}' saved successfully.")
            if unzip:
                with zipfile.ZipFile(file_name, 'r') as zip_ref:
                    zip_ref.extractall(destination_folder)
                    if not quiet:
                        print(f"' - {file_name}' unzipped successfully. ", end="")
                if remove_zip:
                    if os.path.exists(destination_path):
                        os.remove(destination_path)
                        if not quiet:
                            print(f" * Removed zip file '{destination_path}' after extraction.")
                    else:
                        if not quiet:
                            print(f" * Failed to remove zip file. The file '{destination_path}' does not exist")
                else:
                    if not quiet:
                        print()  # Add a newline after extraction message, so it doesn't flow into the next print.

        except OSError as e:
            response["status_code"] = e.errno
            response["message"] = e.strerror
            if not quiet:
                print(f" ! Caught an operating system error wile saving replay: Error {response['status_code']}: {response['message']}")

    else:
        if not quiet:
            print(f" ! Failed to save file. Status code: {response['status_code']} {response['message']}")
    
    return {"status_code": response["status_code"], "request": response["request"], "message": response["message"], "content":response["content"]}

def fetch_replay(profile_id=defaults["profile_id"], match_id=defaults["match_id"], quiet=False):
    '''
    Fetches replay file from the API. Does not save it to disk. To do so,
    pass the return value of this function to save_replay().
    Alternatively, use download_replay() to do both.
    '''
    response = fetch_endpoint("replay", profile_id=profile_id, match_id=match_id, quiet=quiet)
    return response

def download_replay(profile_id=defaults["profile_id"], match_id=defaults["match_id"], destination_folder=defaults["destination_folder"], unzip=defaults["unzip"], remove_zip=defaults["remove_zip"], quiet=False):
    '''
    Fetches a replay file from the API and saves it to disk. Equivalent to using both fetch_replay() and save_replay() in conjunction.
    Can optionaly unzip the replay file and remove the original zip after extraction.
    '''
    replay = fetch_replay(profile_id=profile_id, match_id=match_id, quiet=quiet)
    response = save_replay(
        replay,
        destination_folder=destination_folder,
        unzip=unzip,
        remove_zip=remove_zip,
        quiet=quiet,
        match_id=match_id,
    )
    return response

## <------------------------------------- Stat retrieval endpoints -------------------------------------> ##                       
def fetch_match_details(profile_id=defaults["profile_id"], match_id=defaults["match_id"], quiet=False):
    '''
    Retrieves stats for a given match. Both profile_id and match_id are required. profile_id may be any of the players in the match.
    
    :param profile_id: Profile ID of one of the players in the match.
    :param match_id: Match ID of the match to retrieve stats for.
    '''
    payload = f'{{profileId: {profile_id}, "matchId":"{match_id}"}}'
    response = fetch_endpoint("match_details", data=payload, quiet=quiet)
    return response

def fetch_player_stats(profile_id=defaults["profile_id"], match_type=defaults["match_type"], quiet=False):
    '''
    Retrieves full stats for a given player profile ID. Requires the match type to be specified, as the API endpoint returns different stats based on the match type provided.
    
    :param profile_id: Profile ID of the player to retrieve stats for.
    :param match_type: Match type to retrieve stats for. Use get_match_type_string() for known match types.
    '''
    payload = f'{{profileId: {profile_id}, "matchType":"{match_type}"}}'
    response = fetch_endpoint("player_stats", data=payload, quiet=quiet)
    return response

def fetch_player_campign_stats(profile_id=defaults["profile_id"], quiet=False):
    '''
    Retrieves campaign stats for a given player profile ID.
    
    :param profile_id: Profile ID of the player to retrieve campaign stats for.
    '''
    payload = f'{{profileId: {profile_id}}}'
    response = fetch_endpoint("player_campaign_stats", data=payload, quiet=quiet)
    return response

def fetch_global_stats(quiet=False):
    payload = "{'civid': '4'}"
    response = fetch_endpoint("global_stats", data=payload, quiet=quiet)
    return response

def fetch_player_match_list(profile_id=defaults["profile_id"], game=defaults["game"], sortColumn="dateTime", sort_direction="DESC", match_type=defaults["match_type"], quiet=False):
    '''
    Fetches the match list for a given profile ID. Only the 10 most recent matches are returned.
    Additional parameters can be set to modify the results.

    :param profile_id: Profile ID of the player to retrieve the match list for.
    :param game: The Age of {x} title to use. Could be potentially used for other titles. Currently only tested with age2.
    :param sortColumn: The column to sort the results by. Valid values are dateTime, wins, and civilization.
    :param sort_direction: The direction to sort the results. Valid values are ASC and DESC.
    :param match_type: The type of matches to retrieve. Valid values can be found in the get_match_type_string() helper function. This list is incomplete.
    '''

    #Full payload example for fetching player match list, captured using Fiddler Everywhere:
    #{"gamertag":"unknown user","playerNumber":0,"undefined":null,"game":"age2","profileId":199325,"sortColumn":"dateTime","sortDirection":"DESC","page":1,"recordCount":10,"matchType":"3"}

    #Only profileId, game, sortColumn, sortDirection, and matchType appear to be required. The rest have no effect.
    #   * (Setting "page" as anything other than 1 appears to return an empty list.)
    #   * It is unclear if setting "game" to anything other than age2 will have any effect. (ie. age1, age3, age4, aom)
    #   * sortColumn value can be dateTime, wins, or civilization
    #   * sortDirection value can be ASC or DESC
    #   * matchType values can be found in the get_match_type_string() helper function. This list is incomplete.
    #     TODO: Investigate matchType values further.

    payload = f'{{"game":"{game}","profileId":"{profile_id}","sortColumn":"{sortColumn}", "sortDirection":"{sort_direction}","matchType":"{match_type}"}}'
    response = fetch_endpoint("player_match_list", profile_id=profile_id, data=payload, quiet=quiet)
    return response

def fetch_leaderboard(region="7", match_type="3", console_match_type=15, search_player="", page=1, count=100, sort_column="rank", sort_direction="ASC", quiet=False):
    '''
    Fetches the leaderboard by region and matchtype. Returns the top 100 players per page. Can also be used for player search by name.
    '''
    payload = f'{{"region":"{region}","matchType":"{match_type}","consoleMatchType":{console_match_type},"searchPlayer":"{search_player}","page":{page},"count":{count},"sortColumn":"{sort_column}","sortDirection":"{sort_direction}"}}'
    response = fetch_endpoint("leaderboard", data=payload, quiet=quiet)
    return response

def fetch_player(player_name):
    response = search_for_player(player_name)
    first_result = response.get("content").get("items")[0]
    return first_result
    
def search_for_player(player_name):
    response = fetch_leaderboard(search_player=player_name)
    return response

## <------------------------------------- General purpose endpoint handler -------------------------------------> ##                       

def fetch_endpoint(endpoint_name=None, profile_id=defaults["profile_id"], match_id=defaults["match_id"], headers=defaults["headers"], data=None, quiet=False):
    '''
    Fetches various stats from the Age of Empires API. Endpoint name must be specified.
    This is the general purpose endpoint handler, which can be used to fetch any endpoint defined in the endpoints dictionary.
    For convenience, there are also specific functions for each endpoint, such as fetch_replay() and fetch_player_stats(),
    which call this function with the appropriate parameters.

    :param endpoint_name: The name of the endpoint to fetch. Must be a key in the endpoints dictionary.
    :param profile_id: The profile ID to use in the default payload/url if data is not provided. Default is 199325 (Hera's profile ID).
    :param match_id: The match ID to use in the default payload/url if data is not provided. Default is 453704442 (A match ID from Hera's profile, used for testing).
    :param headers: The headers to include in the request. Default is a set of headers captured from a request made on the official Age of Empires website. May not be necessary for successful requests, but included to match the captured request as closely as possible. Modify as needed.
    :param data: The data to include in the request. For GET requests, this will be used to construct the URL. For POST requests, this will be used as the request body. Must be in the format of a valid JSON string. If not provided, default values will be used based on the profile_id and match_id parameters.
    '''

    #Validate the endpoint
    if not endpoint_name or endpoint_name not in endpoints:
        return {"status_code": 400, "message": f"Invalid or missing endpoint. Valid endpoints are: {list(endpoints.keys())}", "content": None}

    #Default payload
    if not data:
        data = f'{{"matchId":"{match_id}", "profileId":"{profile_id}"}}'
    
    #Fetch the stats from the API
    if not quiet:
        print(f"Fetching stats from endpoint: '{endpoint_name}' with data: {data}")

    if endpoints[endpoint_name]["method"] == "GET":
        values = json.loads(data)
        final_endpoint = Template(endpoints[endpoint_name]["endpoint"]).substitute(**values)
        response = requests.request("GET", final_endpoint)
    elif endpoints[endpoint_name]["method"] == "POST":
        response = requests.request("POST", f"{endpoints[endpoint_name]['endpoint']}", headers=headers, data=data)
    else:
        return {"status_code": 400, "request": response.request, "message": f"Invalid method for endpoint {endpoint_name}", "content": None}
    if response.content:
        content = json.loads(response.content)
    else:
        content = None
    return {"status_code": response.status_code, "request": response.request, "message": response.reason, "content": content}

## <------------------------------------------ Unit Tests ------------------------------------------> ##                       

def run_endpoint_tests(quiet=False, max_content_bytes=None):
    '''
    Runs all API endpoints using default values.
    '''
    match_id = defaults["match_id"] 
    profile_id = defaults["profile_id"]
    match_type = 3

    fetched_replay = fetch_replay(match_id=match_id, quiet=quiet)
    downloaded_replay = download_replay(match_id=match_id, quiet=quiet)
    match_details = fetch_match_details(profile_id=profile_id, match_id=match_id, quiet=quiet)
    player_stats = fetch_player_stats(profile_id=profile_id, match_type=match_type, quiet=quiet)
    player_match_list = fetch_player_match_list(profile_id, match_type=match_type, quiet=quiet)
    campaign_stats = fetch_player_campign_stats(profile_id, quiet=quiet)
    leaderboard = fetch_leaderboard(quiet=quiet)

    if quiet:
        results = [
            ("Replay Fetch", fetched_replay),
            ("Downloaded Replay", downloaded_replay),
            ("Match Details", match_details),
            ("Player Stats", player_stats),
            ("Player Match List", player_match_list),
            ("Campaign Stats", campaign_stats),
            ("Leaderboard", leaderboard),
        ]
        ok_count = sum(1 for _, resp in results if resp.get("status_code") == 200)
        print(f"Run Tests Summary: {ok_count}/{len(results)} OK")
        for name, resp in results:
            status = resp.get("status_code")
            message = resp.get("message", "")
            print(f"- {name}: {status} {message}")
        return

    print("Replay Fetch Response:")
    _print_response(fetched_replay, max_content_bytes=max_content_bytes, quiet=quiet)
    print()

    print("Downloaded Replay Response:")
    _print_status(downloaded_replay, quiet=quiet)
    print()

    print("Match Details Response:")
    _print_response(match_details, max_content_bytes=max_content_bytes, quiet=quiet)
    print()

    print("Player Stats Response:")
    _print_response(player_stats, max_content_bytes=max_content_bytes, quiet=quiet)
    print()

    print("Player Match List Response:")
    _print_response(player_match_list, max_content_bytes=max_content_bytes, quiet=quiet)
    print()

    print("Campaign Stats Response:")
    _print_response(campaign_stats, max_content_bytes=max_content_bytes, quiet=quiet)
    print()

    print("Leaderboard Response:")
    _print_response(leaderboard, max_content_bytes=max_content_bytes, quiet=quiet)
    print()

## <------------------------------------------ Helper functions ------------------------------------------> ##                       
def get_usernames_from_ids(ids:list[str]):
    usernames = [
                fetch_player_stats(
                    profile_id=str(id)
                    ).get("content", {}).get("user", {}).get("userName", {})
                 for id in ids
                 ]
    return usernames

def get_ids_from_usernames(player_names:list[str]):
    ids = [
        fetch_player(
            player_name=player_name
            ).get("rlUserId", {})
        for player_name in player_names
    ]
    return ids

def get_match_type_string(match_type):
    match_type_mapping = {
        1: "Deathmatch",
        2: "Team Deathmatch",
        3: "1v1 RandomMap",
        4: "Team RandomMap",
        13: "Empire Wars",
        14: "Team Empire Wars",
        25: "Return of Rome",
        26: "Team Return of Rome (Unconfirmed)",
        29: "RedBull Wololo: Londinium"
    }
    return match_type_mapping.get(match_type, f"Unknown Match Type ({match_type})")

def _print_response(response, max_content_bytes=None, quiet=False):
    if quiet:
        return
    print(f"Status: {response['status_code']} {response['message']}")
    content = response.get("content")
    if content is None:
        return
    if max_content_bytes is not None and len(content) > max_content_bytes:
        print(f"[Content omitted: {len(content)} bytes > {max_content_bytes} bytes]")
        return
    try:
        decoded = content.decode("utf-8")
        print(decoded)
    except Exception:
        print(content)

def _print_status(response, quiet=False):
    if quiet:
        return
    print(f"Status: {response['status_code']} {response['message']}")

## <------------------------------------- Arg parsing for CLI use -------------------------------------> ##                       
def _add_common_args(parser):
    parser.add_argument("-p", "--profile-id", type=int, default=defaults["profile_id"], help="Profile ID")
    parser.add_argument("-m", "--match-id", type=int, default=defaults["match_id"], help="Match ID")
    parser.add_argument("-g", "--game", type=str, default=defaults["game"], help="Game key (e.g., age2)")

def _parse_args():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--quiet", action="store_true", help="Suppress CLI output")
    common_parser.add_argument("--max-content-bytes", type=int, default=None, help="Max bytes to print for response content")

    parser = argparse.ArgumentParser(
        description="AOE2 API CLI for fetching endpoints and downloading replays.",
        parents=[common_parser],
    )
    subparsers = parser.add_subparsers(dest="command")

    replay_parser = subparsers.add_parser("replay", help="Download a match replay", parents=[common_parser])
    _add_common_args(replay_parser)
    replay_parser.add_argument("-o", "--output", type=str, default=defaults["destination_folder"], help="Destination folder for replay ZIPs")
    replay_parser.add_argument("-u", "--unzip", action="store_true", help="Unzip downloaded replay")
    replay_parser.add_argument("-rm", "--remove-zip", action="store_true", help="Remove ZIP after unzipping")

    match_details_parser = subparsers.add_parser("match-details", help="Fetch match details", parents=[common_parser])
    _add_common_args(match_details_parser)

    player_stats_parser = subparsers.add_parser("player-stats", help="Fetch full player stats given a profile id", parents=[common_parser])
    player_stats_parser.add_argument("-p", "--profile-id", type=int, default=defaults["profile_id"], help="Profile ID")
    player_stats_parser.add_argument("-mt", "--match-type", type=int, default=defaults["match_type"], help="Match type")

    match_list_parser = subparsers.add_parser("player-match-list", help="Fetch player match list", parents=[common_parser])
    match_list_parser.add_argument("-p", "--profile-id", type=int, default=defaults["profile_id"], help="Profile ID")
    match_list_parser.add_argument("-g", "--game", type=str, default=defaults["game"], help="Game key (e.g., age2)")
    match_list_parser.add_argument("-sc", "--sort-column", type=str, default="dateTime", help="Sort column")
    match_list_parser.add_argument("-sd", "--sort-direction", type=str, default="DESC", help="Sort direction (ASC/DESC)")
    match_list_parser.add_argument("-mt", "--match-type", type=int, default=defaults["match_type"], help="Match type")

    campaign_parser = subparsers.add_parser("player-campaign-stats", help="Fetch player campaign stats", parents=[common_parser])
    campaign_parser.add_argument("-p", "--profile-id", type=int, default=defaults["profile_id"], help="Profile ID")

    leaderboard_parser = subparsers.add_parser("leaderboard", help="Fetch leaderboard", parents=[common_parser])
    leaderboard_parser.add_argument("-r", "--region", type=str, default="7", help="Region")
    leaderboard_parser.add_argument("-mt", "--match-type", type=int, default=defaults["match_type"], help="Match type")
    leaderboard_parser.add_argument("-cmt", "--console-match-type", type=int, default=15, help="Console match type")
    leaderboard_parser.add_argument("-s", "--search-player", type=str, default="", help="Search player name")
    leaderboard_parser.add_argument("-p", "--page", type=int, default=1, help="Page number")
    leaderboard_parser.add_argument("-c", "--count", type=int, default=100, help="Count per page")
    leaderboard_parser.add_argument("-sc", "--sort-column", type=str, default="rank", help="Sort column")
    leaderboard_parser.add_argument("-sd", "--sort-direction", type=str, default="ASC", help="Sort direction (ASC/DESC)")

    endpoint_parser = subparsers.add_parser("endpoint", help="Fetch a raw endpoint by name", parents=[common_parser])
    endpoint_parser.add_argument("-e", "--endpoint-name", type=str, required=True, help="Endpoint name")
    endpoint_parser.add_argument("-p", "--profile-id", type=int, default=defaults["profile_id"], help="Profile ID")
    endpoint_parser.add_argument("-m", "--match-id", type=int, default=defaults["match_id"], help="Match ID")
    endpoint_parser.add_argument("-d", "--data", type=str, default=None, help="Raw JSON string payload")

    parser.add_argument("--run-tests", action="store_true", help="Run built-in endpoint tests")

    args = parser.parse_args()

    if args.run_tests:
        run_endpoint_tests(quiet=args.quiet, max_content_bytes=args.max_content_bytes)
        return

    if args.command == "replay":
        result = download_replay(
            profile_id=args.profile_id,
            match_id=args.match_id,
            destination_folder=args.output,
            unzip=args.unzip,
            remove_zip=args.remove_zip,
            quiet=args.quiet,
        )
        _print_status(result, quiet=args.quiet)
        return
    if args.command == "match-details":
        result = fetch_match_details(profile_id=args.profile_id, match_id=args.match_id, quiet=args.quiet)
        _print_response(result, max_content_bytes=args.max_content_bytes, quiet=args.quiet)
        return
    if args.command == "player-stats":
        result = fetch_player_stats(profile_id=args.profile_id, match_type=args.match_type, quiet=args.quiet)
        _print_response(result, max_content_bytes=args.max_content_bytes, quiet=args.quiet)
        return
    if args.command == "player-match-list":
        result = fetch_player_match_list(
            profile_id=args.profile_id,
            game=args.game,
            sortColumn=args.sort_column,
            sort_direction=args.sort_direction,
            match_type=args.match_type,
            quiet=args.quiet,
        )
        _print_response(result, max_content_bytes=args.max_content_bytes, quiet=args.quiet)
        return
    if args.command == "player-campaign-stats":
        result = fetch_player_campign_stats(profile_id=args.profile_id, quiet=args.quiet)
        _print_response(result, max_content_bytes=args.max_content_bytes, quiet=args.quiet)
        return
    if args.command == "leaderboard":
        result = fetch_leaderboard(
            region=args.region,
            match_type=args.match_type,
            console_match_type=args.console_match_type,
            search_player=args.search_player,
            page=args.page,
            count=args.count,
            sort_column=args.sort_column,
            sort_direction=args.sort_direction,
            quiet=args.quiet,
        )
        _print_response(result, max_content_bytes=args.max_content_bytes, quiet=args.quiet)
        return
    if args.command == "endpoint":
        result = fetch_endpoint(
            args.endpoint_name,
            profile_id=args.profile_id,
            match_id=args.match_id,
            data=args.data,
            quiet=args.quiet,
        )
        _print_response(result, max_content_bytes=args.max_content_bytes, quiet=args.quiet)
        return

    parser.print_help()

def main():
    # _parse_args()
    print(fetch_global_stats())

if  __name__ == "__main__":
    main()
