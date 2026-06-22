import logging
from typing import Optional, Dict

logger = logging.getLogger("traingpt.station_resolver")

STATION_ALIASES: Dict[str, str] = {
    "sbc": "SBC", "bangalore": "SBC", "bengaluru": "SBC", "blr": "SBC", "ksr bengaluru": "SBC",
    "ndls": "NDLS", "new delhi": "NDLS", "delhi": "NDLS",
    "sc": "SC", "secunderabad": "SC", "sec": "SC",
    "mas": "MAS", "chennai": "MAS", "central": "MAS", "mgr chennai": "MAS",
    "csmt": "CSMT", "mumbai": "CSMT", "bombay": "CSMT", "chhatrapati shivaji": "CSMT",
    "vskp": "VSKP", "visakhapatnam": "VSKP", "vizag": "VSKP",
    "nzm": "NZM", "nizamuddin": "NZM", "hazrat nizamuddin": "NZM",
    "pdpl": "PDPL", "peddapalli": "PDPL",
    "bza": "BZA", "vijayawada": "BZA",
    "hyb": "HYB", "hyderabad": "HYB", "hyd": "HYB", "hyderabad deccan": "HYB", "nampally": "HYB",
    "rgd": "RGD", "ramagundam": "RGD"
}

def edit_distance(s1: str, s2: str) -> int:
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

def resolve_station(input_str: Optional[str]) -> Optional[str]:
    """
    Resolve a user station input (string or code) using aliases, prefix, and fuzzy matching.
    Returns the uppercase 3-4 letter station code, or None if unresolved.
    """
    if not input_str:
        return None
        
    s_clean = input_str.strip().lower()
    
    # 1. Direct match in aliases mapping
    if s_clean in STATION_ALIASES:
        return STATION_ALIASES[s_clean]
        
    # 2. Check if input matches any code directly
    codes = set(STATION_ALIASES.values())
    for code in codes:
        if code.lower() == s_clean:
            return code
            
    # 3. Whole-word / Prefix matching
    # Split input into words to check for exact word match with any alias
    words = s_clean.split()
    for w in words:
        if w in STATION_ALIASES:
            return STATION_ALIASES[w]
            
    # If the clean input is a prefix of any alias, and is at least 3 chars long
    if len(s_clean) >= 3:
        for alias, code in STATION_ALIASES.items():
            if alias.startswith(s_clean) or s_clean.startswith(alias):
                return code
            
    # 4. Fuzzy edit distance matching
    best_code = None
    min_dist = 999
    for alias, code in STATION_ALIASES.items():
        dist = edit_distance(s_clean, alias)
        # For short aliases (length <= 4), limit edit distance to 1
        # For longer aliases, limit edit distance to 2
        allowed_dist = 1 if len(alias) <= 4 else 2
        if dist < min_dist and dist <= allowed_dist:
            min_dist = dist
            best_code = code
            
    return best_code
