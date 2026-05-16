import datetime

def format_to_mdy(date_val):
    """Converts YYYY-MM-DD to MM/DD/YYYY for institutional compliance."""
    if not date_val: return date_val
    
    if hasattr(date_val, 'strftime'):
        return date_val.strftime('%m/%d/%Y')
        
    if isinstance(date_val, str):
        if '/' in date_val: return date_val
        try:
            parts = date_val.split('-')
            if len(parts) == 3:
                y, m, d = parts
                return f"{m}/{d}/{y}"
        except: pass
        
    return str(date_val)
