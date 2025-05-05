# AI browser use
what is it?
use cases
features
  - built in directions: popups
  - pydantic model
  - connect to open browser
  - hook on each step: screenshot, html
setup
  - scribe PDF
  - convert to steps with AI

watch video
file:///Users/kimberly/home/travel_agent/logs/log-0504-1641/recordings/faf52db3a99ad28da0b140701155f850.webm

```
npx playwright show-trace 46e0b67b-75fd-42f7-bdfa-2fea314ed833.zip
```

# demo
setup: OpenAI key in environment
Airbnb
Booking
  - doesn't work: Click the Check-in date field. Use the date picker to select {date_range}.

# results
cost
  - per 1M tokens
    - input $2.50
    - cached input
    - output $10.00
  - one airbnb run = $0.06 (256,233 tokens)

    - tension between English and more specific directions 
user input

# notes
It really struggles with the date picker. It's a lot of steps, including paging through dates and clicking
buttons. Give up on the date picker and do minimal entry: location. Then update the URL
with dates and adult count.

Websites are complex and some don't want to be accessed by automation.
Maybe English is not a yet a good language for writing a scraper.

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