from datetime import datetime

def validate_date(date_text):
    try:
        if date_text != datetime.strptime(date_text, "%Y-%m-%d").strftime('%Y-%m-%d'):
            raise ValueError
        return True
    except ValueError:
        return False

def string_is_number(str):
    try:
        float(str)
        return True
    except ValueError:
        return False