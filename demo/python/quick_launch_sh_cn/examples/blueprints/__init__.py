from .Agently小助手 import get_blueprint as get_Agently小助手
from .empty import get_blueprint as get_empty
from .smart_one import get_blueprint as get_smart_one

def get_blueprint(blueprint_name):
    if blueprint_name == 'Agently小助手':
        return get_Agently小助手()
    elif blueprint_name == 'empty':
        return get_empty()
    elif blueprint_name == 'smart_one':
        return get_smart_one()