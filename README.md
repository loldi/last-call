# Last Call

An interactive map of American songs that go on record about when the party ends — or swear it never does.

**[View the map →](https://loldi.github.io/last-call/)**

---

## What it is

Hover over a pin and you'll see the song, the artist, and the verdict: a hard stop time (Atlanta, 8 AM; Long Beach, 6 AM) or an infinity symbol for the ones that allegedly never close. 

A year slider underneath lets you scrub from 1949 to 2016 and watch the map fill in. Six songs that never name a city live in a shelf below the map — they still obey the slider.

Amber = the party has a stated end. 
Cyan = it never stops.

---

## How the data was built

Songs like "Welcome to Atlanta" name a specific time ("parties don't stop 'til eight in the morning"), but how many others actually do that? Most just say "all night" and leave it there.  Why do we want to know?  Why not!

To find the real ones, we used the [MetroLyrics 380k dataset](https://github.com/ludovicaschaerf/TMCI_Project) and ran `lyric_miner.py` (a purpose-built scanner) against it. that looks for duration phrases ("break of dawn," "til sunrise," specific clock times, "closing time") alongside city name mentions, geocodes the cities using the offline `geonamescache` gazetteer, and scores each hit. It scanned 362,237 songs and surfaced 762 unique candidates.

From there it was manual review. 

The 762 collapsed fast: 57% matched only on "all night," and most of the remainder had incidental city name-drops that had nothing to do with a party. 

The 45 songs with genuinely hard stop signals (a clock time, dawn, closing time) got a second pass — and of those, three out of four were still false positives on closer read. George Strait's "Dallas" was a reference to the TV show. The Coup's Oakland was street life, not a party. The Game's clock reference was a hype line.

What survived: 17 tracks, 11 on the map, 6 on the shelf, a frankly surprising yield from 362k songs.

Ultimatly we found that "party all night / never stop / til dawn" is everywhere in pop music, but a named city with a real stated end time is genuinely rare. Atlanta's 8 AM and Long Beach's 6 AM are the only two hard clock times in the set.

So there you have it!

---

## The dataset

| Song | Artist | Year | City | Verdict |
|---|---|---|---|---|
| Saturday Night Fish Fry | Louis Jordan | 1949 | New Orleans | Stops (police raid) |
| Viva Las Vegas | Elvis Presley | 1964 | Las Vegas | Never stops |
| Dancing in the Street | Martha & the Vandellas | 1964 | Detroit + many | Never stops |
| Hotel California | Eagles | 1976 | California (somewhere) | Never stops |
| No Sleep Till Brooklyn | Beastie Boys | 1986 | Brooklyn | Never stops |
| All Night Long | Lionel Richie | 1983 | — | Never stops |
| Gin and Juice | Snoop Dogg | 1994 | Long Beach | Stops (6 AM) |
| California Love | 2Pac & Dr. Dre | 1995 | Los Angeles | Never stops |
| Miami | Will Smith | 1998 | Miami | Stops (dawn) |
| Closing Time | Semisonic | 1998 | — | Stops (last call) |
| Welcome to Atlanta | Jermaine Dupri ft. Ludacris | 2001 | Atlanta | Stops (8 AM) |
| Party Hard | Andrew W.K. | 2001 | — | Never stops |
| Mardi Gras in New Orleans | Professor Longhair | 1959 | New Orleans | Stops (Fat Tuesday) |
| Empire State of Mind | Jay-Z & Alicia Keys | 2009 | New York | Never stops |
| TiK ToK | Ke$ha | 2009 | — | Stops (cops/sunrise) |
| I Gotta Feeling | Black Eyed Peas | 2009 | — | Never stops |
| After the Afterparty | Charli XCX | 2016 | — | Never stops |

---

## Tech

The map is a single self-contained HTML file with no runtime dependencies. All the US state geometry is pre-projected at build time via Node + d3-geo from [us-atlas](https://github.com/topojson/us-atlas) TopoJSON, so the browser renders plain SVG paths with no tile server, no API key, and no external libraries to load. The map projection is `geoAlbersUsa`, which places Alaska and Hawaii as insets.

Pin coordinates are the real lat/lng for each city, projected to pixel space and baked into the bundle. Two pins (NYC/Brooklyn and LA/Long Beach) are nudged a few pixels apart so both are hoverable at national scale.

### Files

```
index.html        the map — open this in a browser or deploy as-is
build-geo.mjs     regenerates the baked geometry bundle (Node, d3-geo)
lyric_miner.py    the 362k-song scanner (Python, geonamescache)
states-10m.json   US state geometry source (from us-atlas)
```

### Regenerating the bundle

If you add or change songs, edit the `SONGS` array in `build-geo.mjs`, then:

```bash
npm install d3-geo topojson-client
node build-geo.mjs          # writes bundle.json
# then inject into the template:
python3 -c "
b = open('bundle.json').read()
h = open('tmpl-v3.html').read().replace('/*__BUNDLE__*/', b)
open('index.html','w').write(h)
"
```

### Running the lyric miner

```bash
pip install geonamescache
python3 lyric_miner.py --csv lyrics.csv --out candidates.csv --top 40
```

The corpus (`lyrics.csv`) isn't in this repo — it's 324 MB unzipped. Download it from [the MetroLyrics dataset](https://github.com/ludovicaschaerf/TMCI_Project). The miner outputs a scored candidate CSV.

---

## Adding songs

Everything lives in the `SONGS` array in `build-geo.mjs`. Each entry takes:

```js
{
  t: "Song Title",
  a: "Artist Name",
  y: 2001,                    // year
  place: "City, ST",
  type: "stops",              // or "forever"
  time: "8:00 AM",            // or "∞" for never
  unit: "the cutoff",         // short label shown under the time
  note: "One sentence about the claim.",
  lat: 33.749,
  lng: -84.388,
  dx: 0,                      // optional pixel nudge for overlapping pins
  dy: 0,
}
```

For songs with no named city, add `floater: true` and omit `lat`/`lng`. They'll appear in the shelf below the map.
