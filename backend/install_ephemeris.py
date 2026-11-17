"""Provision official ephemeris data on a network-enabled host.

Core downloads are pinned to an upstream commit. Additional asteroid downloads
use the mirror linked by Astrodienst. Manifest hashes record downloaded bytes;
they are provenance records, not independent authenticity verification.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

REVISION='43c9fe54fc1255a6a83dcb5f4364218ab4034e39'
CORE=['sepl_18.se1','semo_18.se1','seas_18.se1','sefstars.txt']
ASTEROIDS=[5,7,10,16,19,80,1221,1585,1388,1862,408,3811,128,433,149,7066,157,99942]

def download(url,destination):
    request=Request(url,headers={'User-Agent':'Starstruck-Ephemeris-Installer/1.0'})
    with urlopen(request,timeout=60) as response:
        data=response.read(32*1024*1024+1)
    if not data or len(data)>32*1024*1024:
        raise ValueError('Empty or oversized ephemeris file: '+destination.name)
    if destination.suffix=='.se1' and (data.lstrip().startswith(b'<') or data.startswith(b'version https://git-lfs')):
        raise ValueError('Received a web page or pointer instead of ephemeris data')
    destination.parent.mkdir(parents=True,exist_ok=True)
    temp=destination.with_suffix(destination.suffix+'.part')
    temp.write_bytes(data)
    temp.replace(destination)
    return {'file':str(destination.name),'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def install(directory,asteroids=False):
    directory.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for name in CORE:
        manifest.append(download(f'https://raw.githubusercontent.com/aloistr/swisseph/{REVISION}/ephe/{name}',directory/name))
    if asteroids:
        for number in ASTEROIDS:
            relative=f'ast{number//1000}/se{number:05d}s.se1'
            record=download('https://ephe.scryr.io/ephe/'+relative,directory/relative)
            record['file']=relative
            manifest.append(record)
    (directory/'manifest.json').write_text(json.dumps({'upstream_revision':REVISION,'files':manifest},indent=2))
    print(f'Installed {len(manifest)} ephemeris files in {directory}')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,default=Path(__file__).parent/'ephe')
    parser.add_argument('--asteroids',action='store_true')
    args=parser.parse_args()
    install(args.directory,args.asteroids)
