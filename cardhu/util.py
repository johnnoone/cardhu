
from functools import partial
import os.path
import sys
from distutils.errors import DistutilsFileError
from distutils import log
from collections import defaultdict
from setuptools.dist import Distribution
from setuptools.extension import Extension
try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser

try:
    from importlib import import_module
except ImportError:
    pass
from contextlib import contextmanager


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


def assign(name):
    return partial(assign_name, name=name)


def assign_name(config, dest, value, name):
    dest[name] = value
    return dest


def assign_pkg_dir(config, dest, value):
    dest.setdefault('package_dir', {})
    dest['package_dir'][''] = value


def assign_cmds(config, dest, value, dist):
    cmds = {}
    for cls in value:
        cls = load(cls)
        cmds[cls(dist).get_command_name()] = cls
    dest['cmdclass'] = cmds


DISTUTILS2_FORMATS = (
    (('global', 'commands'), multi_type),
    (('global', 'compilers'), multi_type),
    (('global', 'setup_hook'), multi_type),
    (('metadata', 'name'), string_type),
    (('metadata', 'version'), string_type),
    (('metadata', 'platform'), multi_type),
    (('metadata', 'supported-platform'), multi_type),
    (('metadata', 'summary'), string_type),
    (('metadata', 'description'), string_type),
    (('metadata', 'description-file'), file_type),
    (('metadata', 'keywords'), comma_type),
    (('metadata', 'home-page'), string_type),
    (('metadata', 'download-url'), string_type),
    (('metadata', 'author'), string_type),
    (('metadata', 'author-email'), string_type),
    (('metadata', 'maintainer'), string_type),
    (('metadata', 'maintainer-email'), string_type),
    (('metadata', 'license'), string_type),
    (('metadata', 'classifiers'), multi_type),
    (('metadata', 'requires-dist'), multi_type),
    (('metadata', 'provides-dist'), multi_type),
    (('metadata', 'obsoletes-dist'), multi_type),
    (('metadata', 'requires-python'), multi_type),
    (('metadata', 'requires-externals'), multi_type),
    (('metadata', 'project-url'), multi_type),
    (('files', 'packages_root'), string_type),
    (('files', 'packages'), multi_type),
    (('files', 'modules'), multi_type),
    (('files', 'scripts'), multi_type),
    (('files', 'extra_files'), multi_type),
)

EXTENSION_FIELDS = (
    'sources',
    'include_dirs',
    'define_macros',
    'undef_macros',
    'library_dirs',
    'libraries',
    'runtime_library_dirs',
    'extra_objects',
    'extra_compile_args',
    'extra_link_args',
    'export_symbols',
    'swig_opts',
    'depends'
)

D2TO1 = (
    (('global', 'commands'), 'let'),  # cmdclass
    (('global', 'compilers'), False),
    (('global', 'setup_hook'), False),
    (('metadata', 'name'), assign('name')),
    (('metadata', 'version'), assign('version')),
    (('metadata', 'platform'), assign('platforms')),
    (('metadata', 'supported-platform'), None),
    (('metadata', 'summary'), assign('description')),
    (('metadata', 'description'), assign('long_description')),
    (('metadata', 'description-file'), assign('long_description')),
    (('metadata', 'keywords'), assign('keywords')),
    (('metadata', 'home-page'), assign('url')),
    (('metadata', 'download-url'), assign('download_url')),
    (('metadata', 'author'), assign('author')),
    (('metadata', 'author-email'), assign('author_email')),
    (('metadata', 'maintainer'), assign('maintainer')),
    (('metadata', 'maintainer-email'), assign('maintainer_email')),
    (('metadata', 'license'), assign('license')),
    (('metadata', 'classifiers'), assign('classifiers')),
    (('metadata', 'requires-dist'), assign('install_requires')),
    (('metadata', 'provides-dist'), None),  # provides
    (('metadata', 'obsoletes-dist'), None),  # obsoletes
    (('metadata', 'requires-python'), None),
    (('metadata', 'requires-externals'), None),
    (('metadata', 'project-url'), None),
    (('files', 'packages_root'), assign_pkg_dir),
    (('files', 'packages'), None),  # packages
    (('files', 'modules'), None),  # py_modules
    (('files', 'scripts'), None),
    (('files', 'extra_files'), None),
)


def load(target):
    name, _, attr = target.rpartition('.')
    try:
        module = import_module(name)
    except ImportError:
        module = load(name)
    return getattr(module, attr)


def parse_entry_points(parser, dist1):
    if not parser.has_section('entry_points'):
        return
    ep = {}
    for name in parser.options('entry_points'):
        ep[name] = multi_type(parser, ('entry_points', name))
    if ep:
        dist1.setdefault('entry_points', {})
        dist1['entry_points'].update(ep)


def parse_extension(parser, dist1):
    sections = [s for s in parser.sections() if s.startswith('extension:')]
    if not sections:
        return

    mods = []
    for section in sections:
        ext_name = section[10:].strip()
        ext_args = {}
        for option in parser.options(section):
            if option not in EXTENSION_FIELDS:
                continue
            value = multi_type(parser, (section, option))
            if not value:
                continue
            if option == 'define_macros':
                macros = []
                for macro in value:
                    m, _, d = [f.strip() for f in macro.partition('=')]
                    macros.append((m, d or None))
                value = macros
            ext_args[option] = value
        if ext_args:
            mods.append(Extension(ext_name, **ext_args))

    if mods:
        dist1.setdefault('ext_modules', [])
        dist1['ext_modules'].extend(mods)


def cfg_to_args(path='setup.cfg', dist=None):
    '''
    Converts from distutil2 to setup tool args.
    '''
    if not os.path.exists(path):
        raise DistutilsFileError("file '%s' does not exist" %
                                 os.path.abspath(path))

    dist = dist or Distribution()

    parser = RawConfigParser()
    parser.read(path)

    # pure distutils2 parts
    config = defaultdict(dict)
    for (section, option), func in DISTUTILS2_FORMATS:
        if parser.has_option(section, option):
            config[section][option] = func(parser, (section, option))

    package_dir = None
    if parser.has_option('files', 'packages_root'):
        package_dir = config['file']['packages_root']

    with packages(package_dir):
        if parser.has_option('global', 'setup_hook'):
            for target in multi_type(parser, ('global', 'setup_hook')):
                load(target)(config)

    # convert to distutils
    dist1 = dist2_to_args(config, dist=dist)
    register_custom_compilers(config)

    # addendum to distutils entry_points
    parse_entry_points(parser, dist1)

    # addendum to distutils extension:*
    parse_extension(parser, dist1)

    return dist1


@contextmanager
def packages(directory):
    """
    inject package_root to sys.path"""
    cleanup = False
    if directory:
        directory = os.path.abspath(directory)
        if directory not in sys.path:
            cleanup = True
            sys.path.insert(0, directory)
    yield
    if cleanup and directory in sys.path:
        sys.path.remove(directory)


def dist2_to_args(config, dist=None):
    '''
    Converts from distutil2 to distutil1 options.
    '''
    dest = {}
    for (section, option), func in D2TO1:
        if func is None:
            log.warn('key %r not yet implemented', (section, option))
            continue

        if not func:
            continue

        try:
            value = config[section][option]
        except KeyError:
            log.info('%r not found', (section, option))
            continue

        if func == 'let':
            if (section, option) == ('global', 'commands'):
                assign_cmds(config, dest, value, dist)
                continue
            if (section, option) == ('global', 'compilers'):
                continue
            raise Exception('Not implemented')

        func(config, dest, value)

    return dest


def register_custom_compilers(config):
    """Handle custom compilers; this has no real equivalent in distutils, where
    additional compilers could only be added programmatically, so we have to
    hack it in somehow.
    """

    try:
        compilers = config['global']['compilers']
    except KeyError:
        return

    import distutils.ccompiler

    compiler_class = distutils.ccompiler.compiler_class

    for compiler in compilers:
        compiler = load(compiler)

        name = getattr(compiler, 'name', compiler.__name__)
        desc = getattr(compiler, 'description', 'custom compiler %s' % name)
        module_name = compiler.__module__

        if name in compiler_class:
            log.warn('override %r compiler', name)
        compiler_class[name] = (module_name, compiler.__name__, desc)

        # Distutils assumes all compiler modules are in the distutils package
        sys.modules['distutils.' + module_name] = sys.modules[module_name]
