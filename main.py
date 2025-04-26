import asyncio
import base64
import os
from datetime import datetime

from browser_use.controller.service import Controller
from langchain_openai import ChatOpenAI

from browser_use.agent.service import Agent
from browser_use.browser.browser import Browser, BrowserConfig, BrowserContextConfig
from browser_use.browser.context import BrowserContextWindowSize
from pydantic import BaseModel

"""
from https://github.com/browser-use/browser-use/blob/main/examples/use-cases/web_voyager_agent.py
"""

OUTPUT_PATH = "logs"

TASK_BOOKING = """Navigate to https://booking.com/.
Click the "Where are you going?" field.
Type "oahu".
Click "O'ahu" in the drop down.
Use the date picker to select dates May 31 through June 8.
Click the field containing a person icon and text like "3 adults 0 children 1 room".
Set the Adults field value to 3, then click Done.
Click "Search".
Click "Show on map".
Drag, scroll and zoom the map so that it excludes Honolulu and includes the east coast of Oahu, from Punaluu to Kailua.
In the left sidebar, click the checkbox next to Parking.
Repeat the "get details" task for each big blue link in the middle column.
Use the scrollbar on the right side of the middle column to display more results.
Stop after repeating the "get details" task 5 times. 

"get details" task:

Save the big blue link text as the output key "title".
Save the text to the right of the photo below the blue link text as the output key "card".
Save the text formatted as currency starting with $ as the output key "price". Ignore any text in red or formatted with strikethrough.
Click the big blue link.
Click the largest image, wait for the page to load, and take a screenshot.
Save the screenshot with a unique name, and save the  filename in the output key "photos".
Click the Close link in the top right of the modal dialog.
Scroll down the page until Property highlights section is visible. 
Save the screenshot with a unique name, and save the result save the filename in the output key "description".
Scroll down until a table with bed icons and people icons is visible, and take a screenshot.
Save the screenshot with a unique name, and save the result save the filename in the output key "beds".
Get the number of "single" or "twin", "full", "queen" and "king" beds. Do not include "sofa" beds.
Save the bed information in the output key "bed_count".
Close the browser tab and return to the search results page.
Use output to generate JSON in this format and save to results.json
{
  "title": "title",
  "card": "card",
  "price": "price",
  "photos": "photos_filename.png",
  "description": "description",
  "beds": "beds_filename.png",
  "bed_count": {
      "twin": 0,
      "full": 1,
      "queen": 1,
      "king": 0
}
 """

TASK_AIRBNB = """
Task: Find an Airbnb rental in Oahu for 3 adults with at least 2 bedrooms and at least 2 beds.

If a popup, overlay, or modal appears, find and click a button or icon to dismiss it. Look for 'Close', 'X', 'Dismiss', or similar labels.

1. Go to https://www.airbnb.com/
2. Click on Search destinations.
3. Type "Oahu, HI"
5. Click the "Add guests" button.
6. Click the "+" button next to "Adults" three times until it shows 3.
7. Click the "Search" button.
8. Click the "Filters" button.
9. Inside the open modal, scroll down until the "Bedrooms" section is visible.
10. Click the "+" button next to "Bedrooms" twice until it shows 2.
11. Click the "+" button next to "Beds" twice until it shows 2.
12. Click the black button at the bottom that starts with "Show" to apply the filters.
13. Print the URL of the page.
14. Pause and ask the human: "Adjust the map and type 'ok' to continue.", then wait for their response.
15. For each listing block, get the following details:
  - Extract the bold text and save it to "title"
  - Extract the rest of the text and save it to "description"
  - Find an <a> tag where the href attribute starts with "rooms/" and save it to "url"
  - Under  the <picture> element, extract the srcset attribute from the source tag and save it to "picture_url" 
  - Extract the price from text like "$1,234.00 for 5 nights" and save it to "price"
  - Extract the number of beds and save it to "beds"
"""

DETAILS = """
Do these steps for each of the first 3 listings:
1. Click on the image to open the listing.
2. Switch to the new browser tab.
3. Get the URL from the browser tab and save it to "url".
4. Extract the listing title text and save it to "title".
5. Extract the block of text after the bullet points and save it to "description".
6. Scroll down until the red "Reserve" button is visible.
7. Extract the price from text like $1234.00 for 5 nights and save it to "price".
8. Extract the text from the "Where you'll sleep" section and save to "beds".
9. Click the input field under the "Check-in" label.
10. Click the left arrow icon next to the month header until both May 2025 and June 2025 are visible.
11. Close the browser tab to return to the listing page.
"""


# https://github.com/browser-use/browser-use/blob/main/docs/customize/output-format.mdx
class Listing(BaseModel):
    title: str
    url: str
    picture_url: str
    description: str
    price: str
    beds: str


class Listings(BaseModel):
    listings: list[Listing]


async def record_activity(agent_obj: Agent):
    """Hook function that captures and records agent activity at each step"""
    step = agent_obj.state.n_steps
    print(f"--- step hook {step} ---")
    filename = f"step-{step:02}"
    website_html = await agent_obj.browser_context.get_page_html()
    # get the browser url
    try:
        current_page = await agent_obj.browser_context._get_current_page(
            agent_obj.browser_context.session
        )
        website_url = current_page.url
    except Exception as e:
        print(f"error getting url: {e}")
        website_url = "unknown"
    print(f"step {step} url: {website_url}")
    with open(f"{OUTPUT_PATH}/{filename}.html", "w") as f:
        f.write(website_html)
    # base64 encoded screenshot of the current page.
    website_screenshot = await agent_obj.browser_context.take_screenshot()
    write_screenshot(website_screenshot, f"step-{step:02}")


# https://github.com/browser-use/browser-use/blob/main/docs/customize/hooks.mdx
def write_screenshot(data: str, filename: str):
    """Write base64-encoded string to a PNG file."""
    fn = f"{OUTPUT_PATH}/{filename}.png"
    with open(fn, "wb") as f:
        f.write(base64.b64decode(data))
    print(f"wrote screenshot {fn}")


async def main(task: str = TASK_AIRBNB):
    ts = datetime.now().strftime("%H%M")
    # don't know how to get this into the hooks
    global OUTPUT_PATH
    # create logs-ts directory if it doesn't exist
    try:
        os.makedirs(OUTPUT_PATH)
    except FileExistsError:
        pass
    log_path = f"{OUTPUT_PATH}/log-{ts}"
    OUTPUT_PATH = log_path
    print(f"Logging to {OUTPUT_PATH}")
    # OpenAI's GPT-4o models are recommended for best performance.
    llm = ChatOpenAI(model="gpt-4o")
    # https://github.com/browser-use/browser-use/blob/main/browser_use/browser/browser.py
    # hardcodes window-size to screen size
    # offset from get_window_adjustments()
    # non-Chrome: self.config.browser_class firefox, webkit
    # uses self.config.extra_browser_args,
    browser = Browser(
        config=BrowserConfig(
            headless=False,
            disable_security=True,
            new_context_config=BrowserContextConfig(
                disable_security=True,
                minimum_wait_page_load_time=1,  # 3 on prod
                maximum_wait_page_load_time=10,  # 20 on prod
                # no_viewport=True,
                browser_window_size=BrowserContextWindowSize(width=992, height=800),
                trace_path=f"{OUTPUT_PATH}/trace",
            ),
        )
    )
    controller = Controller(output_model=Listings)
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,  #  euse this browser instance and automatically create new contexts for each run()
        controller=controller,
        # validate_output=True,
        # enable_memory=False,
        save_conversation_path=f"{OUTPUT_PATH}/conversation",  # Save chat logs
        # extend_system_message: Add additional instructions to the default system prompt.
    )
    history = await agent.run(
        max_steps=20,
        on_step_end=record_activity,
    )
    result = history.final_result()
    if result:
        parsed: Listings = Listings.model_validate_json(result)
        with open(f"{OUTPUT_PATH}/results.json", "w") as f:
            f.write(parsed.model_dump_json(indent=2))
        for listing in parsed.listings:
            print(listing)
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
    asyncio.run(main())
