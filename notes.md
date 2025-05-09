# notes
It really struggles with the date picker. It's a lot of steps, including paging through dates and clicking
buttons. Give up on the date picker and do minimal entry: location. Then update the URL
with dates and adult count.

Websites are complex and some don't want to be accessed by automation.
Maybe English is not yet a good language for writing a scraper.

## engineering brown bag presentation notes

# What does it do?

browser-use is Python library to connect
  - AI API (I used OpenAI)
  - Your Python code
  - Text instructions
  - Browser (fresh or already open)
  - playwright
    - “powerful and versatile end-to-end (E2E) testing framework for automating web browsers. It's developed and maintained by Microsoft and is designed to be a modern and robust alternative to tools like Selenium.”


### My goals

It’s tedious to re-enter the same filters over and over
  - location, dates, 3 people, non-smoking, WiFi
  - want to see what’s available, multiple dates
  - sites are annoying to use (popups, specials!, irrelevant results)

Sites are missing key (to me) filters
  - double & sofa beds don't count!
  - booking.com: 1 king bed is a “great choice” for 3 adults (no)

Cut through the noise, save time, focus on the fun parts

The dream (from the web_voyager_agent.py example):
“"Find and book a hotel in Paris with suitable accommodations for a family of four (two adults and two children) offering free cancellation for the dates of February 14-21, 2025. on https://www.booking.com/”


### Local setup

OpenAPI
  - create account, add $
  - set OPENAI_API_KEY in environment

install browser-use
  - pip install browser-use

install browsers so playwright can use them
  - npx playwright install

Scribe to ChatGPT to English steps

copy example and start editing
  - web_voyager_agent.py

Note: quick start if you understand this, huge lift if not

### Interesting features

  - step hooks for custom actions: screenshot, html
  - session recordings
  - system instructions to close popups: great use case for vague actions
  - output to pydantic models: convert unstructured info to structured
  - connect to open logged in browser
    - but also scary: read how ChatGPT agent [spent $31 on a dozen eggs](https://www.washingtonpost.com/technology/2025/02/07/openai-operator-ai-agent-chatgpt/)

### Demo 1: Airbnb

  - scribe to capture steps: Airbnb_steps.pdf
  - ask ChatGPT to create steps from Scribe PDF: "write the task as text for use with browser-use library"
    - steps in airbnb_v1.txt
  - step through code
    - set up browser: new browser, clear cookies, save recordings
    - merge params with steps
    - output to pydantic model
  - run: `make airbnb1 ; make logs`
    - closes popups!
    - gets caught in date picker
    - doesn't wait for a human
    - extracts data!
    - gets lost and ends
  - view outputs: logs-airbnb1/
    - recordings/ for video
    - conversationX for system instructions
    - agent.log for console output
    - step-02.png for screenshot
    - results.json for output
  - update script, try again
  - give up: user input

### Demo 2: Booking
  - task: from booking.com, get listings near a landmark and extract details
    - initial revision: do what I did, more but simpler extract steps
    - learned from previous: simpler extract, add examples
    - booking_date.txt
  - run: `make booking1 ; make logs`
    - so far so good
    - uh oh what happened to the date picker
    - step 9 finally set the dates
    - whoo made it to the listings page
    - what happened to the date picker
    - now it's off the rails
  - this stuff is hard
  - give up: date picker
  - URL hacking: save skip clicking buttons
    - booking.txt

### Results

Who is this for?
  - requires Python, playwright, OpenAI, browser with remote debugging
  - debugging is hard: iterating on prompts, matching logs with traces, iterations are slow
  - use this to generate a “compiled” version? but Selenium browser does this, simpler

Is English the right language?
  - great for popups; didn’t work for date pickers
  - maintenance unknown
  - mixing English & DOM selectors?

Prototype / one off usage: $2.50/1M tokens
  - personal use: $0.34/run is great (if it works)


## URL hacking

explain how to modify initial url to get final url
initial url = 
https://www.booking.com/searchresults.html?ss=Northeastern+University%2C+Boston%2C+Massachusetts%2C+United+States&map=1&efdco=1&label=gen173nr-1FCAEoggI46AdIM1gEaIkCiAEBmAExuAEHyAEM2AEB6AEB-AECiAIBqAIDuALQnuDABsACAdICJDY1MTIxNTY4LWUxN2EtNDUzMC05MTJlLWYwMzlkZmEzY2M3MtgCBeACAQ&aid=304142&lang=en-us&sb=1&src_elem=sb&src=index&dest_id=900064725&dest_type=landmark&ac_position=0&ac_click_type=b&ac_langcode=en&ac_suggestion_list_length=1&search_selected=true&search_pageview_id=6a7f07e8c22e00c4&ac_meta=GhA2YTdmMDdlOGMyMmUwMGM0IAAoATICZW46I05vcnRoZWFzdGVybiBVbml2ZXJzaXR5LCBCb3N0b24sIE1BQABKAFAA&group_adults=2&no_rooms=1&group_children=0#map_opened

final url =
https://www.booking.com/searchresults.html?label=gen173nr-1FCAEoggI46AdIM1gEaIkCiAEBmAExuAEHyAEM2AEB6AEB-AECiAIBqAIDuALQnuDABsACAdICJDY1MTIxNTY4LWUxN2EtNDUzMC05MTJlLWYwMzlkZmEzY2M3MtgCBeACAQ&aid=304142&ss=Northeastern+University%2C+Boston%2C+Massachusetts%2C+United+States&map=1&efdco=1&lang=en-us&dest_id=900064725&dest_type=landmark&ac_position=0&ac_click_type=b&ac_langcode=en&ac_suggestion_list_length=1&search_selected=true&search_pageview_id=6a7f07e8c22e00c4&group_adults=2&no_rooms=1&group_children=0&order=distance_from_search&nflt=hotelfacility%3D107%3Bhotelfacility%3D16

### 🔧 Steps to Modify the Initial URL to the Final URL

1. **Remove the following parameters** from the query string:
   - `sb=1`
   - `src_elem=sb`
   - `src=index`

2. **Add the following parameters** to the end of the query string:
   - `order=distance_from_search`
   - `nflt=hotelfacility%3D107%3Bhotelfacility%3D16`

3. **Remove the URL fragment** (at the end of the URL):
   - Delete `#map_opened` (or any `#...`)

4. **(Optional)** Reorder the parameters if desired — this has no effect on functionality.
Let