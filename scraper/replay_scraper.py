from aoe2api import aoe2api
import time
import argparse

defaults = {
    "request_interval": 5,
    "back_off_delay": 20,
    "back_off_multiplier": 2,
    "max_back_off_delay": 300,
    "start_id": 453891485,
    "end_id":   450000000,
    "endpoint_name": "replay",
    "unzip_replays": False,
    "remove_zip": False,
    "scrape_state_file": "scrape_state.txt",
    "resume": False,
    "count_backwards": False,
}

def save_scrape_state(current_id, end_id, filename=defaults["scrape_state_file"]):
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

def scrape_replays(
    resume=defaults["resume"],
    endpoint_name=defaults["endpoint_name"],
    start_id=defaults["start_id"],
    end_id=defaults["end_id"],
    request_interval=defaults["request_interval"],
    back_off_delay=defaults["back_off_delay"],
    back_off_multiplier=defaults["back_off_multiplier"],
    max_back_off_delay=defaults["max_back_off_delay"],
    unzip=defaults["unzip_replays"],
    remove_zip=defaults["remove_zip"],
    scrape_state_file=defaults["scrape_state_file"],
    count_backwards=defaults["count_backwards"],
):
    current_back_off_delay = back_off_delay
    if resume:
        last_id_scraped, end_id_scraped = get_last_scrape_state(filename=scrape_state_file)
        print("Resuming from last scrape state: start_id =", last_id_scraped, "end_id =", end_id_scraped)
        if last_id_scraped is not None:
            start_id = last_id_scraped - 1 if count_backwards else last_id_scraped + 1
        end_id = end_id_scraped if end_id_scraped is not None else end_id
    
    n = start_id
    step = -1 if count_backwards else 1
    def has_more(current_id, target_id):
        return current_id > target_id if count_backwards else current_id < target_id

    while n >= end_id if count_backwards else n <= end_id:
        response = aoe2api.fetch_endpoint(endpoint_name=endpoint_name, match_id=n, profile_id=1)
        aoe2api.save_replay(response, unzip=unzip, remove_zip=remove_zip)
        if response["status_code"] == 200 or response["status_code"] == 404:
            current_back_off_delay = back_off_delay  # Reset backoff delay on success or not found
            save_scrape_state(n, end_id, filename=scrape_state_file)
            if has_more(n, end_id):
                time.sleep(request_interval)
            n += step
        else:
            print(f" ! BACK OFF, EH! Error {response['status_code']}: {response['message']}. Backing off for {current_back_off_delay}s.")
            time.sleep(current_back_off_delay)

            current_back_off_delay = min(
                current_back_off_delay * back_off_multiplier,
                max_back_off_delay
            )

def main(args):
    scrape_replays(
        resume=args.resume,
        endpoint_name=args.endpoint_name,
        start_id=args.start_id,
        end_id=args.end_id,
        request_interval=args.request_interval,
        back_off_delay=args.back_off_delay,
        back_off_multiplier=args.back_off_multiplier,
        max_back_off_delay=args.max_back_off_delay,
        unzip=args.unzip,
        remove_zip=args.remove_zip,
        scrape_state_file=args.scrape_state_file,
        count_backwards=args.count_backwards,
    )

def _build_arg_parser():
    parser = argparse.ArgumentParser(description="Scrape Age of Empires 2 replays from the API.")
    _add_arg_parser_options(parser)
    return parser

def _add_arg_parser_options(parser):
    parser.add_argument("-r", "--resume", action="store_true", help="Resume from last scrape state")
    parser.add_argument("-s", "--start_id", type=int, default=defaults["start_id"], help="Starting match ID")
    parser.add_argument("-e", "--end_id", type=int, default=defaults["end_id"], help="Ending match ID")
    parser.add_argument("-i", "--request-interval", type=int, default=defaults["request_interval"], help="Delay between requests in seconds")
    parser.add_argument("-bd", "--back-off-delay", type=int, default=defaults["back_off_delay"], help="Base delay (seconds) when rate limited")
    parser.add_argument("-bm", "--back-off-multiplier", type=int, default=defaults["back_off_multiplier"], help="Exponential backoff multiplier per rate limit hit")
    parser.add_argument("-bmax", "--max-back-off-delay", type=int, default=defaults["max_back_off_delay"], help="Max backoff delay (seconds) when rate limited")
    parser.add_argument("-ep", "--endpoint-name", type=str, default=defaults["endpoint_name"], help="Endpoint name to scrape")
    parser.add_argument("-sf", "--scrape-state-file", type=str, default=defaults["scrape_state_file"], help="Path to scrape state file")
    parser.add_argument("-u", "--unzip", action="store_true", help="Unzip downloaded replays")
    parser.add_argument("-rm", "--remove_zip", action="store_true", help="Remove zip files after unzipping")
    parser.add_argument("-cb", "--count-backwards", action="store_true", help="Count down from start_id to end_id")

def _parse_args():
    parser = _build_arg_parser()
    return parser.parse_args()

if __name__ == "__main__":
    args = _parse_args()
    main(args)
