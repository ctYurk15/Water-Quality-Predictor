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

def string_to_bool(str):
    result = str
    if str == 'True': result = True
    elif str == 'False': result = False
    return result

def number_to_bool_string(str):
    result = str
    if str == '1': result = 'True'
    elif str == '0': result = 'False'
    return result