import collections
import weakref

from pyardrone import at


class Config(collections.ChainMap):

    def __init__(self, owner):
        self.owner = weakref.proxy(owner)
        self.data = LazyConfigDict(owner)
        self.updates = dict()
        super().__init__(self.updates, self.data)

    def __getattr__(self, name):
        return ConfigCategory(self, name)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.owner.send(at.CONFIG(key, value))

    def clear_cache(self):
        self.updates.clear()
        self.data.clear()


class ConfigCategory:

    __slots__ = ('_context', '_name')

    def __init__(self, context, name):
        super().__setattr__('_context', weakref.proxy(context))
        super().__setattr__('_name', name)

    def __getattr__(self, name):
        return self._context[self._get_option_name(name)]

    def __setattr__(self, name, value):
        self._context[self._get_option_name(name)] = value

    def __repr__(self):
        return '<ConfigCategory {}>'.format(self._name)

    def _get_option_name(self, name):
        return '{}:{}'.format(self._name, name)


class LazyConfigDict(dict):

    __slots__ = ('owner', 'retrieved')

    def __init__(self, owner):
        super().__init__()
        self.owner = weakref.proxy(owner)
        self.retrieved = False

    def __getitem__(self, key):
        if not self.retrieved:
            self.retrieve()
        return super().__getitem__(key)

    def retrieve(self):
        self.retrieved = True
        raw_config = self.owner.get_raw_config()
        self.update(iter_config_file(raw_config))

    def clear(self):
        self.retrieved = False
        super().clear()


def unpack_value(value):
    if value == 'TRUE':
        return True
    elif value == 'FALSE':
        return False
    elif value.startswith('{') and value.endswith('}'):
        return [unpack_value(item) for item in value[1:-1].split()]
    elif value.isdigit():
        return int(value)
    else:
        try:
            return float(value)
        except:
            return value


def iter_config_file(confstr):
    for row in confstr.splitlines():
        name, raw_value = row.split(' = ')
        yield name, unpack_value(raw_value)