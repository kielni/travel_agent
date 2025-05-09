import argparse
import asyncio
import base64
import logging
import os
from datetime import datetime, date, timedelta
from typing import Type

from dateutil import parser as date_parser
from browser_use.controller.service import Controller
from dateutil.relativedelta import relativedelta
from langchain_openai import ChatOpenAI

from browser_use.agent.service import Agent
from browser_use.browser.browser import Browser, BrowserConfig, BrowserContextConfig
from browser_use.browser.context import BrowserContextWindowSize
from pydantic import BaseModel

"""
Use a browser to browse lodging sites, apply additional filters, and return structured results.
started from https://github.com/browser-use/browser-use/blob/main/examples/use-cases/web_voyager_agent.py
"""

OUTPUT_PATH = "logs"
START_TS = datetime.now()

log = logging.getLogger("main")

"""
Hook for capturing additional information on each step: url, html, screenshots.
"""


async def record_activity(agent_obj: Agent):
    """Save html and screenshot on each step.

    https://github.com/browser-use/browser-use/blob/main/docs/customize/hooks.mdx
    """
    global START_TS
    step = agent_obj.state.n_steps - 1
    elapsed = round((datetime.now() - START_TS).total_seconds())
    log.info(f"--- step hook {step} --- {elapsed}s\n")
    filename = f"step-{step:02}"
    website_html = await agent_obj.browser_context.get_page_html()
    # get the browser url
    try:
        current_page = await agent_obj.browser_context._get_current_page(
            agent_obj.browser_context.session
        )
        website_url = current_page.url
    except Exception as e:
        log.error(f"error getting url: {e}")
        website_url = "unknown"
    log.info(f"step {step} url: {website_url}")
    with open(f"{OUTPUT_PATH}/{filename}.html", "w") as f:
        f.write(website_html)
    await write_screenshot(agent_obj, f"step-{step:02}")


async def write_screenshot(agent_obj: Agent, filename: str):
    """Take a screenshot and write base64-encoded string to a PNG file."""
    # base64 encoded screenshot of the current page.
    data = await agent_obj.browser_context.take_screenshot()
    fn = f"{OUTPUT_PATH}/{filename}.png"
    with open(fn, "wb") as f:
        f.write(base64.b64decode(data))
    log.info(f"wrote screenshot {fn}")


"""
Pydantic models for output.

https://github.com/browser-use/browser-use/blob/main/docs/customize/output-format.mdx
"""


# BROWNBAG 4
class BaseListing(BaseModel):
    title: str
    url: str
    price: str
    bed_count: int
    bed_type: str


class AirbnbListing(BaseListing):
    picture_url: str
    description: str


class AirbnbListings(BaseModel):
    listings: list[AirbnbListing]


def setup_airbnb_task(location: str, script: str) -> tuple[str, Type[BaseModel]]:
    """Load task steps from file and set up with start_url and city"""
    location_parts = location.split(", ")
    city = location_parts[0]
    url_location = "--".join(location_parts)
    query_location = "%2C%20".join(location_parts)
    start_url = (
        f"https://www.airbnb.com/s/{url_location}/homes?"
        "refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&"
        "price_filter_input_type=2&channel=EXPLORE&"
        "date_picker_type=calendar&adults=3&"
        f"source=structured_search_input_header&search_type=filter_change&query={query_location}&"
        "search_mode=regular_search&price_filter_num_nights=7&"
    )
    with open(script or "airbnb_listing.txt") as f:
        task_text = f.read()
    task = task_text.format(start_url=start_url, results_in=city)
    return task, AirbnbListings


class BookingListing(BaseListing):
    uncounted_bed_count: int
    uncounted_bed_count_type: str


class BookingListings(BaseModel):
    listings: list[BookingListing]


def setup_booking_task(
    location: str, start_date: date, end_date: date, script: str
) -> tuple[str, Type[BaseModel]]:
    with open(script or "booking.txt") as f:
        task_text = f.read()
    # date format Sat Jul 26 - Sun Jul 27
    start_month = start_date.strftime("%B %Y")
    next_month = (start_date + relativedelta(months=1)).strftime("%B %Y")
    task = task_text.format(
        location=location,
        start_month=start_month,
        next_month=next_month,
        start_date=start_date,
        end_date=end_date,
        start_yymmdd=start_date.strftime("%Y-%m-%d"),
        end_yymmdd=end_date.strftime("%Y-%m-%d"),
    )
    return task, BookingListings


def setup_logs():
    """Write logs from this script and browser-use to a directory with a timestamp."""
    ts = datetime.now().strftime("%m%d-%H%M")
    # don't know how else to get this into the hooks
    global OUTPUT_PATH
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    log_path = f"{OUTPUT_PATH}/log-{ts}"
    log_file = os.path.join(log_path, "agent.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)  # Ensure the directory exists
    OUTPUT_PATH = log_path

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s\t%(message)s", datefmt="%H:%M:%S"
    )
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # https://github.com/browser-use/browser-use/issues/999
    # browser_use disables log propagation so root logging config doesn't work
    logging.getLogger("browser_use").addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)
    log.setLevel(logging.INFO)
    print(f"Logging to {OUTPUT_PATH}")


def setup_task(
    location: str, site: str, from_dt: date, to_dt: date, script: str = None
) -> tuple[str, Type[BaseModel]]:

    task = output_model = None
    if site == "airbnb":
        task, output_model = setup_airbnb_task(location, script)
    elif site == "booking":
        task, output_model = setup_booking_task(location, from_dt, to_dt, script)
    with open(f"{OUTPUT_PATH}/task.txt", "w") as f:
        f.write(task)
    return task, output_model


def setup_dates(from_str: str, to_str: str) -> tuple[date, date]:
    """Parse dates from strings and return as date objects."""
    if from_str:
        from_date = date_parser.parse(from_str).date()
    else:
        from_date = date.today() + timedelta(days=42)
    if to_str:
        to_date = date_parser.parse(to_str).date()
    else:
        to_date = from_date + timedelta(days=4)
    return from_date, to_date


def new_browser() -> Browser:
    """Open a new browser.

    https://github.com/browser-use/browser-use/blob/main/browser_use/browser/browser.py
    """
    log.info("opening a new browser")
    return Browser(
        config=BrowserConfig(
            headless=False,
            disable_security=True,
            new_context_config=BrowserContextConfig(
                minimum_wait_page_load_time=2,
                maximum_wait_page_load_time=10,
                clear_cookies=True,
                save_recording_path=f"{OUTPUT_PATH}/recordings",
                # this doesn't seem to do anything: window-size is hardcoded to screen size
                browser_window_size=BrowserContextWindowSize(width=992, height=800),
                trace_path=f"{OUTPUT_PATH}/trace",
            ),
        )
    )


def existing_browser() -> Browser:
    """Connect to an existing open browser.

    https://github.com/browser-use/browser-use/blob/250032c7dfd2ae5f28ebea800fea909b46c00a53/docs/customize/real-browser.mdx#L2
    start Chrome with
    """
    # /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug-profile &
    log.info("opening an existing browser")
    return Browser(
        config=BrowserConfig(
            browser_binary_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS path (Adjust if needed)
            connect_config={
                "ws_endpoint": "ws://localhost:9222"  # Point to the remote debugging port
            },
            new_context_config=BrowserContextConfig(
                minimum_wait_page_load_time=2,
                maximum_wait_page_load_time=10,
                save_recording_path=f"{OUTPUT_PATH}/recordings",
                trace_path=f"{OUTPUT_PATH}/trace",
            ),
        ),
    )


async def main(
    location: str, site: str, from_str: str, to_str: str, script: str = None
):
    from_dt, to_dt = setup_dates(from_str, to_str)
    task, output_model = setup_task(location, site, from_dt, to_dt, script)
    if site == "sce":
        browser = existing_browser()
    else:
        browser = new_browser()
    log.info(f"loading data from {site} with model {output_model}")
    controller = Controller(output_model=output_model)
    agent = Agent(
        task=task,
        # OpenAI's GPT-4o models are recommended for best performance.
        llm=ChatOpenAI(model="gpt-4o"),
        browser=browser,  #  reuse this browser instance and automatically create new contexts for each run()
        controller=controller,
        save_conversation_path=f"{OUTPUT_PATH}/conversation",  # Save chat logs
        # extend_system_message: Add additional instructions to the default system prompt.
    )
    history = await agent.run(
        max_steps=20,
        on_step_end=record_activity,
    )
    result = history.final_result()
    if result:
        parsed = output_model.model_validate_json(result)
        with open(f"{OUTPUT_PATH}/results.json", "w") as f:
            f.write(parsed.model_dump_json(indent=2))
        for listing in parsed.listings:
            print(listing)
        log.info(f"{len(parsed.listings)} results")
    """
history.urls()              # List of visited URLs
history.screenshots()       # List of screenshot paths
history.action_names()      # Names of executed actions
history.extracted_content() # Content extracted during execution
history.errors()           # Any errors that occurred
history.model_actions()     # All actions with their parameters
    """
    history.save_to_file(f"{OUTPUT_PATH}/history.json")


if __name__ == "__main__":
    setup_logs()
    parser = argparse.ArgumentParser()
    # "Hauula, Oahu, HI" airbnb
    # "Northeastern University, Boston, MA" booking --from_date 2025-07-26 --to_date 2025-07-27
    parser.add_argument("location", type=str, help="location to search")
    parser.add_argument("site", type=str, choices=["airbnb", "booking"])
    parser.add_argument("--from_date", type=str, help="start date ")
    parser.add_argument("--to_date", type=str, help="end date")
    parser.add_argument("--script", type=str, help="script to run")
    args = parser.parse_args()
    asyncio.run(
        main(args.location, args.site, args.from_date, args.to_date, args.script)
    )
