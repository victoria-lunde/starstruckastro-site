"""Starstruck natal chart calculations. No interpretations or persistence.

Swiss Ephemeris licensing must be resolved before exposing this as a service.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import math
import threading

SIGNS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
PLANETS = {'Sun':0,'Moon':1,'Mercury':2,'Venus':3,'Mars':4,'Jupiter':5,'Saturn':6,'Uranus':7,'Neptune':8,'Pluto':9}
# Swiss built-in IDs; numbered asteroids use AST_OFFSET + catalog number.
MINOR = {'Chiron':15,'Pholus':16,'Ceres':17,'Pallas':18,'Juno':19,'Vesta':20}
ASTEROIDS = {'Hygiea':10,'Astraea':5,'Iris':7,'Psyche':16,'Amor':1221,'Union':1585,'Sappho':80,'Aphrodite':1388,'Apollo':1862,'Fortuna':19,'Fama':408,'Karma':3811,'Nemesis':128,'Eros':433,'Medusa':149,'Nessus':7066,'Dejanira':157,'Apophis':99942}
POINTS = {'Mean lunar nodes':10,'True lunar nodes':11,'Mean Black Moon Lilith':12,'True Black Moon Lilith':13}
OPTIONAL = set(MINOR) | set(ASTEROIDS) | set(POINTS) | {'Algol','Part of Fortune'}
LOCK = threading.RLock()

class ChartError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

def local_to_utc(day, clock, zone, fold=None):
    """Roundtrip both folds: reject DST gaps and ask about repeated local times."""
    try:
        z = ZoneInfo(zone)
        parsed_clock = time.fromisoformat(clock)
        if parsed_clock.tzinfo is not None:
            raise ValueError('Expected a local clock time')
        naive = datetime.combine(date.fromisoformat(day), parsed_clock)
    except (ValueError, ZoneInfoNotFoundError, TypeError):
        raise ChartError('invalid_time', 'Enter a valid date, time, and IANA time zone.')
    candidates = []
    for f in (0, 1):
        aware = naive.replace(tzinfo=z, fold=f)
        utc = aware.astimezone(timezone.utc)
        if utc.astimezone(z).replace(tzinfo=None) == naive and utc not in [v[1] for v in candidates]:
            candidates.append((f, utc))
    if not candidates:
        raise ChartError('nonexistent_local_time', 'This local time did not exist because the clock moved forward. Check the recorded birth time.')
    if len(candidates) > 1 and fold is None:
        raise ChartError('ambiguous_local_time', 'This local time occurred twice. Select the first or second occurrence.')
    if fold not in (None, 0, 1):
        raise ChartError('invalid_fold', 'Time occurrence must be 0 or 1.')
    return next((u for f,u in candidates if f == fold), candidates[0][1])

def placement(longitude, speed=None, rising=None):
    lon = longitude % 360
    sign = int(lon // 30)
    result = {'longitude':round(lon,8),'sign':SIGNS[sign],'degree':round(lon % 30,6),'house':None if rising is None else (sign-int((rising%360)//30))%12+1}
    if speed is not None:
        result.update(speed=round(speed,8), retrograde=speed < 0)
    return result

def aspects(bodies):
    result=[]
    items=list(bodies.items())
    for i,(a,x) in enumerate(items):
        if a not in PLANETS: continue
        for b,y in items[i+1:]:
            if b not in PLANETS: continue
            sep=abs((x['longitude']-y['longitude']+180)%360-180)
            for angle,name in [(0,'conjunction'),(60,'sextile'),(90,'square'),(120,'trine'),(180,'opposition')]:
                orb=abs(sep-angle)
                if orb <= 6:
                    result.append({'a':a,'b':b,'aspect':name,'orb':round(orb,4)})
    return result

def validate(payload):
    if not isinstance(payload, dict):
        raise ChartError('invalid_input','Expected a chart object.')
    if isinstance(payload.get('latitude'), bool) or isinstance(payload.get('longitude'), bool):
        raise ChartError('invalid_coordinates','Coordinates must be numbers.')
    try:
        lat=float(payload['latitude']);lon=float(payload['longitude'])
        d=date.fromisoformat(payload['date'])
    except (ValueError, KeyError, TypeError, OverflowError):
        raise ChartError('invalid_input','Birth date, latitude and longitude are required.')
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ChartError('invalid_coordinates','Latitude or longitude is outside its valid range.')
    if not date(1800,1,1) <= d <= datetime.now(timezone.utc).date():
        raise ChartError('unsupported_date','This version supports birth dates from 1800 through today.')
    tradition=payload.get('tradition','tropical')
    if tradition not in ('tropical','sidereal'):
        raise ChartError('invalid_tradition','Select tropical or sidereal (Lahiri).')
    selected=payload.get('points',[])
    if not isinstance(selected,list) or len(selected)>40 or any(not isinstance(x,str) or x not in OPTIONAL for x in selected):
        raise ChartError('invalid_body','One or more selected bodies are unsupported.')
    if payload.get('house_system','W') != 'W':
        raise ChartError('invalid_houses','Only Whole Sign houses are supported in this version.')
    return lat,lon,list(dict.fromkeys(selected)),tradition

def calculate(payload, swe, ephe_path):
    lat,lon,selected,tradition=validate(payload)
    unknown=payload.get('unknown_time',False)
    if not isinstance(unknown,bool): raise ChartError('invalid_time','Unknown-time flag must be true or false.')
    utc=local_to_utc(payload['date'],'12:00' if unknown else payload.get('time',''),payload.get('timezone',''),None if unknown else payload.get('fold'))
    if utc > datetime.now(timezone.utc): raise ChartError('future_time','Birth time must be in the past.')
    warnings=[]
    if unknown: warnings.append('Unknown birth time: positions are a local-noon reference. Houses, Rising, MC, Fortune and time-sensitive aspects are omitted. Moon range spans the local calendar day.')
    jd=lambda t:swe.julday(t.year,t.month,t.day,t.hour+t.minute/60+t.second/3600)
    with LOCK:
        swe.set_ephe_path(ephe_path)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        flags=swe.FLG_SWIEPH | swe.FLG_SPEED | (swe.FLG_SIDEREAL if tradition=='sidereal' else 0)
        t=jd(utc)
        rising=None;angles=None;cusps=[]
        if not unknown:
            try:
                c,a=swe.houses_ex(t,lat,lon,b'W',swe.FLG_SIDEREAL if tradition=='sidereal' else 0)
                rising=a[0];angles={'rising':placement(a[0]),'midheaven':placement(a[1])};cusps=[placement(x) for x in c]
            except Exception:
                raise ChartError('houses_unavailable','House calculation failed for this location and time.')
        bodies={};unavailable=[]
        def calc(name,ident,required=False):
            try:
                values,returned=swe.calc_ut(t,ident,flags)
                if not returned & swe.FLG_SWIEPH:
                    raise RuntimeError('Swiss ephemeris file unavailable; fallback rejected')
                bodies[name]=placement(values[0],values[3],rising)
            except Exception:
                if required: raise ChartError('ephemeris_unavailable','Planetary ephemeris data is unavailable. The service will not substitute approximate results.')
                unavailable.append({'name':name,'reason':'Required ephemeris data is unavailable for this date.'})
        for name,ident in PLANETS.items():calc(name,ident,True)
        for name in selected:
            if name in MINOR:calc(name,MINOR[name])
            elif name in ASTEROIDS:calc(name,swe.AST_OFFSET+ASTEROIDS[name])
            elif name in POINTS:
                calc(name,POINTS[name])
                if name in ('Mean lunar nodes','True lunar nodes') and name in bodies:
                    bodies[name+' · South']=placement(bodies[name]['longitude']+180,bodies[name]['speed'],rising)
            elif name=='Algol':
                try:
                    values,canonical,returned=swe.fixstar2_ut('Algol',t,flags)
                    bodies[name]=placement(values[0],None,rising)
                    bodies[name]['kind']='fixed_star'
                except Exception:unavailable.append({'name':'Algol','reason':'Fixed-star catalog unavailable.'})
            elif name=='Part of Fortune' and not unknown:
                # Sun altitude determines the day/night formula, not a house heuristic.
                values,_=swe.calc_ut(t,swe.SUN,swe.FLG_SWIEPH)
                altitude=swe.azalt(t,swe.ECL2HOR,(lon,lat,0),0,15,(values[0],values[1],values[2]))[1]
                sun=bodies['Sun']['longitude'];moon=bodies['Moon']['longitude']
                bodies[name]=placement(rising+(moon-sun if altitude>=0 else sun-moon),None,rising)
        moon_range=None
        if unknown:
            begin=local_to_utc(payload['date'],'00:00',payload['timezone'],0)
            end=local_to_utc((date.fromisoformat(payload['date'])+timedelta(days=1)).isoformat(),'00:00',payload['timezone'],0)
            moon_range=[]
            for edge in (begin,end):
                v,r=swe.calc_ut(jd(edge),swe.MOON,flags)
                if not r & swe.FLG_SWIEPH: raise ChartError('ephemeris_unavailable','Moon ephemeris unavailable.')
                moon_range.append(placement(v[0]))
    return {'engine':'Swiss Ephemeris','engine_version':swe.version,'zodiac':tradition,'ayanamsha':'Lahiri' if tradition=='sidereal' else None,'house_system':'Whole Sign' if not unknown else None,'utc':utc.isoformat(),'unknown_time':unknown,'angles':angles,'cusps':cusps,'bodies':bodies,'aspects':[] if unknown else aspects(bodies),'aspect_policy':'Major planet-to-planet aspects, 6 degree maximum orb.','moon_day_range':moon_range,'unavailable':unavailable,'warnings':warnings}
