
import os.path
from distutils.errors import DistutilsFileError
from distutils import log
from collections import defaultdict
try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser

try:
    from importlib import import_module
except ImportError:
    pass


def string_type(parser, src):
    return parser.get(*src)


def multi_type(parser, src):
    elements = parser.get(*src)
    return [element.strip() for element in elements.strip().split('\n')]


def file_type(parser, src):
    with open(parser.get(*src), 'r') as file:
        return file.read()


def comma_type(parser, src):
    elements = parser.get(*src)
    splitter = ',' if ',' in elements else None
    return [element.strip() for element in elements.split(splitter)]


D2TO1 = (
    (('global', 'commands'), None, multi_type),
    (('global', 'compilers'), None, multi_type),
    (('global', 'setup_hook'), None, multi_type),
    (('metadata', 'name'), 'name', string_type),
    (('metadata', 'version'), 'version', string_type),
    (('metadata', 'platform'), None, multi_type),
    (('metadata', 'supported-platform'), None, multi_type),
    (('metadata', 'summary'), 'description', string_type),
    (('metadata', 'description'), 'long_description', string_type),
    (('metadata', 'description-file'), 'long_description', file_type),
    (('metadata', 'keywords'), 'keywords', comma_type),
    (('metadata', 'home-page'), 'url', string_type),
    (('metadata', 'download-url'), None, string_type),
    (('metadata', 'author'), 'author', string_type),
    (('metadata', 'author-email'), 'author_email', string_type),
    (('metadata', 'maintainer'), None, string_type),
    (('metadata', 'maintainer-email'), None, string_type),
    (('metadata', 'license'), 'license', string_type),
    (('metadata', 'classifiers'), 'classifiers', multi_type),
    (('metadata', 'requires-dist'), 'install_requires', multi_type),
    (('metadata', 'provides-dist'), None, multi_type),
    (('metadata', 'obsoletes-dist'), None, multi_type),
    (('metadata', 'requires-python'), None, multi_type),
    (('metadata', 'requires-externals'), None, multi_type),
    (('metadata', 'project-url'), None, multi_type),
    (('files', 'packages_root'), None, string_type),
    (('files', 'packages'), None, multi_type),
    (('files', 'modules'), None, multi_type),
    (('files', 'scripts'), None, multi_type),
    (('files', 'extra_files'), None, multi_type),
)


def cfg_to_args(path='setup.cfg'):
    '''
    Converts from distutil2 to setup tool args.
    '''
    if not os.path.exists(path):
        raise DistutilsFileError("file '%s' does not exist" %
                                 os.path.abspath(path))

    parser = RawConfigParser()
    parser.read(path)

    config = defaultdict(dict)
    for (section, option), _, func in D2TO1:
        if parser.has_option(section, option):
            config[section][option] = func(parser, (section, option))

    # play with setup_hook
    if parser.has_option('global', 'setup_hook'):
        for target in multi_type(parser, ('global', 'setup_hook')):
            module_name, func = target.rsplit('.', 1)
            module = import_module(module_name)
            getattr(module, func)(config)

    return dist2_to_args(config)


def dist2_to_args(data):
    '''
    Converts from distutil2 to distutil1 options.
    '''
    config = {}
    for (section, option), dist1, func in D2TO1:
        if dist1 is None:
            log.warn('key %r not yet implemented', (section, option))
            continue
        try:
            config[dist1] = data[section][option]
        except KeyError as error:
            log.info('%r not found', (section, option))
    return config
