"""Bounded field evidence, without identities, credentials or raw responses."""
import math
import re

PRIVATE = re.compile(r'token|password|secret|auth|ssid|address|name|certificate|serial|(?:^|[._])(?:id|mac|ip)(?:$|[._])', re.I)
RADIO = re.compile(r'rssi|signal|mesh|radio|link|connection|frequency|channel|band|snr|noise|speed\.(?:speedRating|numericSpeedRating)$', re.I)
ENUM = re.compile(r'(?:(?:AP|CONNECTION_TYPE|MESH|LINK|SIGNAL|QUALITY|BAND)_[A-Z_0-9]+|GOOD|GREAT|OK|FAIR|POOR|WEAK|EXCELLENT|WIRED|WIRELESS|ETHERNET)', re.I)

def radio_schema(payload):
    schema, evidence = set(), {}
    visited = 0
    def walk(value, path='', depth=0):
        nonlocal visited
        visited += 1
        if depth > 14 or visited > 15000 or len(schema)>600: return
        if isinstance(value, dict):
            for key,item in value.items():
                key = key if isinstance(key,str) and re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]{0,55}',key) else '*'
                walk(item, path+'.'+key if path else key, depth+1)
        elif isinstance(value, list):
            for item in value[:1000]: walk(item,path+'[]',depth+1)
        else:
            schema.add(path+':'+type(value).__name__)
            if not RADIO.search(path) or PRIVATE.search(path): return
            if isinstance(value,(float,int)) and not isinstance(value,bool):
                try:
                    if not math.isfinite(value): return
                except OverflowError: return
                sample=value
            elif isinstance(value,str) and path.endswith('numericSpeedRating') and re.fullmatch(r'\d{1,3}',value): sample=int(value)
            elif isinstance(value,str) and ENUM.fullmatch(value): sample=value
            else: return
            samples=evidence.setdefault(path,[])
            if sample not in samples and len(samples)<12: samples.append(sample)
    walk(payload)
    return {'fields':sorted(schema),'radio_samples':evidence}
