import json

from jinja2 import is_undefined


def env_json(value):
    # pass undefined values on down the pipeline
    if is_undefined(value):
        return value
    result = json.loads(value)
    return result
