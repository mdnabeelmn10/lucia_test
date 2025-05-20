import time
from django.utils.crypto import get_random_string

def generate_unix_id():
    return int(time.time() * 1000)
