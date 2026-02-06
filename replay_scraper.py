import aoe2api
import time
import argparse

defaults = {
    "scrape_delay": 0,
    "slow_down_delay": 5,
    "slow_down_increment": 10,
    "max_slow_down_delay": 60,
    "start_id": 450000000,
    "end_id":   453704499,
    "endpoint_name": "replay",
    "unzip_replays": False,
    "remove_zip": False,
    "scrape_state_file": "scrape_state.txt",
    "resume": False,
}

def save_scrape_state(current_id, end_id,filename=defaults["scrape_state_file"]): 
    with open(filename, "w") as f:
        f.write(f"{current_id},{end_id}")

def get_last_scrape_state(filename=defaults["scrape_state_file"]):
    try:
        with open(filename, "r") as f:
            content = f.read().strip().split(",")
            last_id = int(content[0])
            end_id = int(content[1])
            return last_id, end_id
    except FileNotFoundError:
        return None, None

def scrape_replays(resume=defaults["resume"], endpoint_name=defaults["endpoint_name"], start_id = defaults["start_id"], end_id = defaults["end_id"], delay = defaults["scrape_delay"], slow_down_delay=defaults["slow_down_delay"], slow_down_increment=defaults["slow_down_increment"], max_slow_down_delay=defaults["max_slow_down_delay"], unzip=defaults["unzip_replays"], remove_zip = defaults["remove_zip"], scrape_state_file=defaults["scrape_state_file"]):
    current_slow_down_delay = slow_down_delay
    if resume:
        last_id_scraped, end_id_scraped = get_last_scrape_state(filename=scrape_state_file)
        print("Resuming from last scrape state: start_id =", last_id_scraped, "end_id =", end_id_scraped)
        start_id = last_id_scraped + 1 if last_id_scraped is not None else start_id
        end_id = end_id_scraped if end_id_scraped is not None else end_id
    
    n = start_id
    while n <= end_id:
        response = aoe2api.fetch_endpoint(endpoint_name=endpoint_name, match_id=n, profile_id=1)
        aoe2api.save_replay(response, unzip=unzip, remove_zip=remove_zip)
        if response["status_code"] == 200 or response["status_code"] == 404:
            current_slow_down_delay = slow_down_delay  # Reset backoff delay on success or not found
            save_scrape_state(n, end_id, filename=scrape_state_file)
            if n < end_id:
                time.sleep(delay)
            n += 1
        elif response["status_code"] == 429:
            print("Rate limit exceeded. Slowing down...")
            current_slow_down_delay = min(
                current_slow_down_delay + slow_down_increment,
                max_slow_down_delay
            )
            time.sleep(current_slow_down_delay)

def main(args):
    scrape_replays(
        resume=args.resume,
        endpoint_name=args.endpoint_name,
        start_id=args.start_id,
        end_id=args.end_id,
        delay=args.delay,
        slow_down_delay=args.slow_down_delay,
        slow_down_increment=args.slow_down_increment,
        max_slow_down_delay=args.max_slow_down_delay,
        unzip=args.unzip,
        remove_zip=args.remove_zip,
        scrape_state_file=args.scrape_state_file,
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Age of Empires 2 replays from the API.")
    parser.add_argument("-r", "--resume", action="store_true", help="Resume from last scrape state")
    parser.add_argument("-s", "--start_id", type=int, default=defaults["start_id"], help="Starting match ID")
    parser.add_argument("-e", "--end_id", type=int, default=defaults["end_id"], help="Ending match ID")
    parser.add_argument("-d", "--delay", type=int, default=defaults["scrape_delay"], help="Delay between requests in seconds")
    parser.add_argument("-sd", "--slow-down-delay", type=int, default=defaults["slow_down_delay"], help="Base delay (seconds) when rate limited")
    parser.add_argument("-si", "--slow-down-increment", type=int, default=defaults["slow_down_increment"], help="Delay increment (seconds) per rate limit hit")
    parser.add_argument("-sm", "--max-slow-down-delay", type=int, default=defaults["max_slow_down_delay"], help="Max backoff delay (seconds) when rate limited")
    parser.add_argument("-ep", "--endpoint-name", type=str, default=defaults["endpoint_name"], help="Endpoint name to scrape")
    parser.add_argument("-sf", "--scrape-state-file", type=str, default=defaults["scrape_state_file"], help="Path to scrape state file")
    parser.add_argument("-u", "--unzip", action="store_true", help="Unzip downloaded replays")
    parser.add_argument("-rm", "--remove_zip", action="store_true", help="Remove zip files after unzipping")
    args = parser.parse_args()
    main(args)
