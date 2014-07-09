__all__ = ['DefaultGetDict', 'IgnoreDict']

from collections import defaultdict
from fnmatch import fnmatch


class DefaultGetDict(defaultdict):
    """Like defaultdict, but the get() method also sets and returns the default
    value.
    """

    def get(self, key, default=None):
        if default is None:
            default = self.default_factory()
        return super(DefaultGetDict, self).setdefault(key, default)


class IgnoreDict(dict):
    """A dictionary that ignores any insertions in which the key is a string
    matching any string in `ignore`.  The ignore list can also contain wildcard
    patterns using '*'.
    """

    def __init__(self, ignore):
        self.ignore = ignore

    def __setitem__(self, key, val):
        if any(fnmatch(key, pat) for pat in self.ignore):
            return
        super(IgnoreDict, self).__setitem__(key, val)
