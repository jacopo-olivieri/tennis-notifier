# Camden Active booking platform (Lincoln's Inn Fields)

Findings from unauthenticated requests on 2026-10-04, about 17:00 BST, from a residential connection (about 40 requests). Nothing was logged into or booked.

## Platform
- Camden's own **Camden Active** site, an ASP.NET WebForms app (Rocktime, Telerik) behind Cloudflare. Not ClubSpark, Better or Legend.
- Three courts, each with its own page:
  - Court 1: https://camdenactive.camden.gov.uk/courses/detail/171/lincoln-s-inn-fields-tennis-court-1/ (fdCourseEventId=192)
  - Court 2: https://camdenactive.camden.gov.uk/courses/detail/176/lincoln-s-inn-fields-tennis-court-2/ (fdCourseEventId=199)
  - Court 3: https://camdenactive.camden.gov.uk/courses/detail/177/lincoln-s-inn-fields-tennis-court-3/ (fdCourseEventId=200)
- Deep link for a free slot: `/courses/book.aspx?fdCourseEventId=192&fdDate=DD/MM/YYYY&fdTime=HH`. Without a session it redirects to login.

## Reading availability
- Availability is public. There is no JSON API: the grid is server-rendered HTML showing one Sun–Sat week of hourly rows.
- Booked slot: `<li class="facility-closed">…<span class="facility-hour">08:00 </span><span>Booked</span>…`
- Free slot: `<li><a class="facility-book" href="/courses/book.aspx?…&fdDate=12/10/2026&fdTime=10">…!Book!…`
- Hours that don't exist are left out. Hours shrink with dusk: 08:00–17:00 in October, 08:00–15:00 in November.
- To get later weeks, GET the page, then POST it back with all hidden inputs (`__VIEWSTATE`, `__VIEWSTATEGENERATOR`, `__EVENTVALIDATION`, `__AT`, `__SCROLLPOSITIONX/Y`) plus `__EVENTTARGET=ctl00$PageContent$btnNextWeek` and an empty `__EVENTARGUMENT`. Keep the cookies (`RTSI`, `__cf_bm`). Each postback moves forward one week, so the view state is chained.
- About 7s per request, so a full scan (3 courts × about 5 weeks) takes minutes.
- No Cloudflare challenge was seen with urllib and a Mozilla User-Agent. robots.txt allows everything. Cloud-hosted IPs have not been tested.
- Samples: `sample_week0_court1.html`, `sample_week1_court1.html`.

## Booking window
- The terms say courts can be booked "up to five weeks in advance".
- Tested on Sun 4 Oct: the last bookable day was Sat 7 Nov, i.e. today + 34 days.
- **The grid shows "!Book!" beyond the window**, so anything past today + 34 days must be ignored.
- **The time of day a new day is released is unknown.**

## Demand and cancellations
- The current week was 100% booked on all courts. Further weeks had 9–52 free slots per court per week. Early-morning and weekend slots are the scarce ones.
- Bookings are **non-refundable** (only a rain credit), so freed slots are probably rare. It's unknown whether cancelled or unpaid slots come back.
- Price is about £13.90 (seniors and under-16s £5.55). Not verified.

## Prior art
No existing tool targets Camden Active. ClubSpark watchers such as https://github.com/pdd27673/10s-court-monitor are useful only as models for alerting.
