import decimal

def granularity_to_minutes(granularity: str) -> int:
    """Convert granularity string to total seconds"""
    granularity_map = {
        'S20': 20,  # 20 seconds
        'M1': 60,   # 1 minute
        'M5': 300,  # 5 minutes
        'M15': 900, # 15 minutes
        'M30': 1800, # 30 minutes
        'H1': 3600, # 1 hour
        'H4': 14400, # 4 hours
        'D': 86400,  # 24 hours
        'W': 604800, # 7 days
        'M': 2592000 # 30 days (approximation)
    }

    if granularity not in granularity_map:
        raise ValueError(f"Unsupported granularity: {granularity}")
    
    return granularity_map[granularity]

def get_trade_multipler(price_1):
    if str(price_1).index('.') >= 3:  # JPY pair
        multiplier = 0.01
    else:
        multiplier = 0.0001
    
    return multiplier

def get_decimals_places(value):
    d_p = decimal.Decimal(str(value))
    d_p = abs(d_p.as_tuple().exponent)
    
    # Decimals places
    return d_p
