from distutils import log
from distutils.errors import DistutilsSetupError
from .util import cfg_to_args
from .coll import DefaultGetDict, IgnoreDict


finalized = set()


def cardhu(dist, attr, value):
    """
    Implements the actual cardhu setup() keyword.
    :param dist: setuptools.dist.Distribution obj
    :param attr: cardhu
    :param value: value of cardhu
    """

    if not value or dist in finalized:
        return
    finalized.add(dist)

    log.info('cardhu hook %s %s %s', dist, attr, value)

    path = 'setup.cfg'
    try:
        attrs = cfg_to_args(path)
    except Exception as error:
        raise DistutilsSetupError(
            'Error parsing %s: %s: %s' % (path, error.__class__.__name__,
                                          error.args[0]))

    # Repeat some of the Distribution initialization code with the newly
    # provided attrs
    if attrs:
        # Skips 'options' and 'licence' support which are rarely used; may add
        # back in later if demanded
        for key, val in attrs.items():
            if hasattr(dist.metadata, 'set_' + key):
                getattr(dist.metadata, 'set_' + key)(val)
            elif hasattr(dist.metadata, key):
                setattr(dist.metadata, key, val)
            elif hasattr(dist, key):
                setattr(dist, key, val)
            else:
                msg = 'Unknown distribution option: %s' % repr(key)
                log.warn(msg)

    # Re-finalize the underlying Distribution
    dist.finalize_options()

    ignore = ['pre_hook.*', 'post_hook.*']
    dist.command_options = DefaultGetDict(lambda: IgnoreDict(ignore))
