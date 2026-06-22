import {readFileSync, writeFileSync} from 'fs';
import {feature} from 'topojson-client';
import {geoAlbersUsa, geoPath} from 'd3-geo';

const W = 900, H = 560;

// authoritative dataset (paraphrased claims, no lyrics). located = has lat/lng.
const SONGS = [
  {t:"Welcome to Atlanta", a:"Jermaine Dupri ft. Ludacris", y:2001, place:"Atlanta, GA", type:"stops", time:"8:00 AM", unit:"the cutoff",
   note:"Names a hard cutoff of eight in the morning, the only precise clock time in the set apart from Gin and Juice.", lat:33.749, lng:-84.388},
  {t:"Miami", a:"Will Smith", y:1998, place:"Miami, FL", type:"stops", time:"Dawn", unit:"on the beach",
   note:"The party runs all night on the sand and wraps when the sun comes up.", lat:25.7617, lng:-80.1918},
  {t:"Gin and Juice", a:"Snoop Dogg", y:1994, place:"Long Beach, CA", type:"stops", time:"6:00 AM", unit:"house party",
   note:"Still going strong at 2 AM while mom's away, and everyone clears out by six in the morning.", lat:33.7701, lng:-118.1937, dx:-3, dy:16},
  {t:"Empire State of Mind", a:"Jay-Z & Alicia Keys", y:2009, place:"New York, NY", type:"forever", time:"\u221E", unit:"never sleeps",
   note:"New York gets framed as the city that never sleeps, so there's no closing time on offer.", lat:40.7128, lng:-74.0060},
  {t:"No Sleep Till Brooklyn", a:"Beastie Boys", y:1986, place:"Brooklyn, NY", type:"forever", time:"\u221E", unit:"no sleep",
   note:"The road-trip party flatly refuses to sleep until the crew makes it back home.", lat:40.6782, lng:-73.9442, dx:11, dy:13},
  {t:"Dancing in the Street", a:"Martha & the Vandellas", y:1964, place:"Detroit, MI + many", type:"forever", time:"\u221E", unit:"all summer",
   note:"An open invitation to dance all summer, shouted across Chicago, New Orleans, New York, Philadelphia, Baltimore, DC and the Motor City.", lat:42.3314, lng:-83.0458},
  {t:"Viva Las Vegas", a:"Elvis Presley", y:1964, place:"Las Vegas, NV", type:"forever", time:"\u221E", unit:"24h+ won't do",
   note:"Even forty extra hours in a day wouldn't be enough; day and night just blur together.", lat:36.1699, lng:-115.1398},
  {t:"California Love", a:"2Pac & Dr. Dre", y:1995, place:"Los Angeles, CA", type:"forever", time:"\u221E", unit:"floor stays full",
   note:"Out west the dance floors reportedly never empty out, day or night.", lat:34.0522, lng:-118.2437},
  {t:"Hotel California", a:"Eagles", y:1976, place:"California (somewhere)", type:"forever", time:"\u221E", unit:"can't leave",
   note:"Guests are free to check out whenever, but somehow can never get out the door. The eerie one, where the location is more metaphor than map.", lat:36.3, lng:-121.3},
  {t:"Mardi Gras in New Orleans", a:"Professor Longhair", y:1959, place:"New Orleans, LA", type:"stops", time:"Fat Tuesday", unit:"then Lent",
   note:"The carnival rolls for weeks, then tradition slams it shut at midnight on Fat Tuesday when Lent begins. A cutoff set by the calendar, not the clock.", lat:29.9511, lng:-90.0715},
  {t:"Saturday Night Fish Fry", a:"Louis Jordan", y:1949, place:"New Orleans, LA", type:"stops", time:"The raid", unit:"cops bust it",
   note:"A fish fry on Rampart Street that rocks till dawn, then gets raided by the police, who haul everyone off to jail. Often cited as a contender for the first rock and roll record.", lat:29.9580, lng:-90.0700, dx:-16, dy:7},
  {t:"Closing Time", a:"Semisonic", y:1998, place:"An unnamed bar", type:"stops", time:"Last call", unit:"lights up",
   note:"One last drink, the lights come on, everybody out. Famously also a coded metaphor about being born.", floater:true},
  {t:"All Night Long", a:"Lionel Richie", y:1983, place:"A street party, no city", type:"forever", time:"\u221E", unit:"forever",
   note:"A multilingual block party billed to run all night and, per the chorus, basically forever.", floater:true},
  {t:"TiK ToK", a:"Ke$ha", y:2009, place:"Some city, unnamed", type:"stops", time:"Cops / sunrise", unit:"or 'til kicked out",
   note:"The chorus insists the party never ends, but the verse admits it runs only until the police shut it down or the sun comes up.", floater:true},
  {t:"Party Hard", a:"Andrew W.K.", y:2001, place:"No city named", type:"forever", time:"\u221E", unit:"party hard",
   note:"The purest distillation of the genre: whenever it is party time, the only setting is maximum. No clock, no address, no off switch.", floater:true},
  {t:"I Gotta Feeling", a:"Black Eyed Peas", y:2009, place:"No city named", type:"forever", time:"\u221E", unit:"do it all night",
   note:"Tonight is billed as a good night, and the stated plan is to keep doing it all night. A massive anthem that never names a place.", floater:true},
  {t:"After the Afterparty", a:"Charli XCX", y:2016, place:"No city (Ibiza, declined)", type:"forever", time:"\u221E", unit:"into the afterlife",
   note:"Clocked at nearly 4 AM and still feeling fine, the plan is to stay till morning and run it all back. Charli called it partying into the afterlife, and the lyric even waves off Ibiza as unnecessary.", floater:true},
];

const topo = JSON.parse(readFileSync('usatlas/package/states-10m.json'));
const states = feature(topo, topo.objects.states);
const nation = feature(topo, topo.objects.nation);
const proj = geoAlbersUsa().fitSize([W, H], states);
const path = geoPath(proj);

const round = d => d ? d.replace(/-?\d+\.\d+/g, m => Math.round(+m)) : d;
const statePaths = states.features.map(f => round(path(f))).filter(Boolean);
const nationPath = round(path(nation));

// bake pixel coords into located songs
const songs = SONGS.map(s => {
  if (s.floater) return s;
  const xy = proj([s.lng, s.lat]);
  if (!xy) { console.error("WARN no projection for", s.t); return s; }
  return {...s, px: +(xy[0] + (s.dx||0)).toFixed(1), py: +(xy[1] + (s.dy||0)).toFixed(1)};
});

writeFileSync('bundle.json', JSON.stringify({W, H, statePaths, nationPath, songs}));
console.log(`bundle: ${statePaths.length} states, ${songs.filter(s=>!s.floater).length} pins, ${songs.filter(s=>s.floater).length} floaters`);
console.log("sample pin:", songs.find(s=>!s.floater).t, songs.find(s=>!s.floater).x, songs.find(s=>!s.floater).y);
