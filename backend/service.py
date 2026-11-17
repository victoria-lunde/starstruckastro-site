"""Run: uvicorn service:app --host 0.0.0.0 --port 8000"""
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from fastapi import FastAPI, Request as WebRequest
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from chart_engine import calculate, ChartError

app=FastAPI(title='Starstruck Chart Engine',docs_url=None,redoc_url=None,openapi_url=None)
origins=[o.strip() for o in os.getenv('ALLOWED_ORIGINS','https://starstruckastro.com,https://www.starstruckastro.com,https://starstruckastro-site.pages.dev').split(',') if o.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['POST','GET'],allow_headers=['Content-Type'])

@app.middleware('http')
async def private_responses(request,call_next):
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response

@app.get('/health')
def health():
    return {'service':'starstruck-chart-engine','enabled':os.getenv('ENGINE_ENABLED')=='true','locations_configured':bool(os.getenv('GEOAPIFY_API_KEY'))}

@app.get('/api/locations')
def locations(q:str=''):
    if not 3 <= len(q.strip()) <= 100:
        return JSONResponse({'error':'Enter between 3 and 100 characters.'},status_code=400)
    key=os.getenv('GEOAPIFY_API_KEY')
    if not key:return JSONResponse({'error':'Location search is not configured yet.'},status_code=503)
    query=urlencode({'text':q.strip(),'type':'city','format':'json','limit':6,'apiKey':key})
    try:
        with urlopen(Request('https://api.geoapify.com/v1/geocode/autocomplete?'+query,headers={'Accept':'application/json'}),timeout=8) as res:
            data=json.load(res)
        results=[]
        for p in data.get('results',[]):
            zone=p.get('timezone',{}).get('name')
            if zone and 'lat' in p and 'lon' in p:
                results.append({'label':p.get('formatted',''),'latitude':p['lat'],'longitude':p['lon'],'timezone':zone})
        return {'results':results,'attribution':'Powered by Geoapify | © OpenStreetMap contributors'}
    except Exception:return JSONResponse({'error':'Location lookup is unavailable. Try again shortly.'},status_code=502)

@app.post('/api/chart')
async def chart(request:WebRequest):
    # No raw birth details, names or payloads are persisted or logged by this service.
    # Add edge rate limits before public activation. CORS is not abuse protection.
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>8192:return JSONResponse({'error':'Request too large.'},status_code=413)
    if os.getenv('ENGINE_ENABLED')!='true':return JSONResponse({'error':'Chart engine is not activated yet.'},status_code=503)
    if os.getenv('SWISSEPH_LICENSE_MODE') not in ('professional','agpl'):
        return JSONResponse({'error':'Chart service licensing is not configured.'},status_code=503)
    try:
        payload=json.loads(raw)
        if not isinstance(payload,dict):
            return JSONResponse({'error':'Expected a chart object.'},status_code=400)
    except (ValueError,UnicodeError):return JSONResponse({'error':'Invalid chart request.'},status_code=400)
    try:
        import swisseph as swe
        path=os.getenv('EPHEMERIS_PATH',str(Path(__file__).parent/'ephe'))
        # Keep blocking CPU work and global Swiss state off the event loop.
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(calculate,payload,swe,path)
    except ChartError as e:return JSONResponse({'code':e.code,'error':str(e)},status_code=422 if e.code!='ephemeris_unavailable' else 503)
    except ImportError:return JSONResponse({'error':'Chart calculation dependency unavailable.'},status_code=503)
    except Exception:return JSONResponse({'error':'Chart calculation failed. No chart was saved.'},status_code=500)
