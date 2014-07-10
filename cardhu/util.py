
from functools import partial
import os.path
import sys
from distutils.errors import DistutilsError
from distutils.errors import DistutilsFileError
from distutils.errors import DistutilsModuleError
from distutils import log
from collections import defaultdict
from setuptools.command import __all__ as command_list
from setuptools.dist import Distribution
from setuptools.extension import Extension

try:
    from importlib import import_module
except ImportError:
    pass
from contextlib import contextmanager
from .errors import LoadError
from .parsing import ConfigParser, parse_string, parse_multi, parse_file, parse_csv


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


def assign_pkg_data(config, dest, value):
    dest.setdefault('extra_files', defaultdict(dict))
    dest['extra_files'][''].update(value)

DISTUTILS2_FORMATS = (
    (('global', 'commands'), parse_multi),
    (('global', 'compilers'), parse_multi),
    (('global', 'setup_hook'), parse_multi),
    (('metadata', 'name'), parse_string),
    (('metadata', 'version'), parse_string),
    (('metadata', 'platform'), parse_multi),
    (('metadata', 'supported-platform'), parse_multi),
    (('metadata', 'summary'), parse_string),
    (('metadata', 'description'), parse_string),
    (('metadata', 'description-file'), parse_file),
    (('metadata', 'keywords'), parse_csv),
    (('metadata', 'home-page'), parse_string),
    (('metadata', 'download-url'), parse_string),
    (('metadata', 'author'), parse_string),
    (('metadata', 'author-email'), parse_string),
    (('metadata', 'maintainer'), parse_string),
    (('metadata', 'maintainer-email'), parse_string),
    (('metadata', 'license'), parse_string),
    (('metadata', 'classifiers'), parse_multi),
    (('metadata', 'requires-dist'), parse_multi),
    (('metadata', 'provides-dist'), parse_multi),
    (('metadata', 'obsoletes-dist'), parse_multi),
    (('metadata', 'requires-python'), parse_multi),
    (('metadata', 'requires-externals'), parse_multi),
    (('metadata', 'project-url'), parse_multi),
    (('files', 'packages_root'), parse_string),
    (('files', 'packages'), parse_multi),
    (('files', 'modules'), parse_multi),
    (('files', 'scripts'), parse_multi),
    (('files', 'extra_files'), parse_multi),
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
    (('files', 'packages'), assign('packages')),
    (('files', 'modules'), assign('py_modules')),
    (('files', 'scripts'), assign('scripts')),
    (('files', 'extra_files'), assign_pkg_data),
)


def load(target):
    name, _, attr = target.rpartition('.')
    try:
        module = import_module(name)
    except (ValueError, LoadError):
        raise LoadError('module {!r} does not exists'.format(target))
    except ImportError:
        module = load(name)
    return getattr(module, attr)


def parse_entry_points(parser, dist1):
    if not parser.has_section('entry_points'):
        return
    ep = {}
    for name in parser.options('entry_points'):
        ep[name] = parse_multi(parser, ('entry_points', name))
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
            value = parse_multi(parser, (section, option))
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


def parse_extras_require(parser, dist1):
    print(parser._sections)
    if not parser.has_option('metadata', 'requires-extra'):
        return

    data = parser.getmulti('metadata', 'requires-extra', nested=True)
    if data:
        dist1.setdefault('extra_require', {})
        for elt in data:
            dist1['extra_require'].update(elt)


def cfg_to_args(path='setup.cfg', dist=None):
    '''
    Converts from distutil2 to setup tool args.
    '''
    if not os.path.exists(path):
        raise DistutilsFileError("file '%s' does not exist" %
                                 os.path.abspath(path))

    dist = dist or Distribution()

    parser = ConfigParser()
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
            for target in parse_multi(parser, ('global', 'setup_hook')):
                load(target)(config)

    # convert to distutils
    dist1 = dist2_to_args(config, dist=dist)
    register_custom_compilers(config)

    # addendum to distutils extras_require
    parse_extras_require(parser, dist1)

    # addendum to distutils entry_points
    parse_entry_points(parser, dist1)

    # addendum to distutils extension:*
    parse_extension(parser, dist1)
    wrap_commands(dist1, dist)
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


def wrap_commands(dist1, dist):
    dist.parse_config_files()

    # override every commands with pre/post hook dispatching
    dist1.setdefault('cmdclass', {})

    subparser = ConfigParser()
    here = os.path.abspath(os.path.dirname(__file__))
    subparser.read(os.path.join(here, 'common.cfg'))

    commands = set(command_list)
    commands.update(cmd for cmd, _ in dist.get_command_list())
    commands.update(dist1['cmdclass'].keys())
    for cmd in sorted(commands):
        try:
            cls = dist1['cmdclass'][cmd]
        except KeyError:
            cls = dist.get_command_class(cmd)
        pre_hook = getattr(cls, 'pre_hook', {})
        post_hook = getattr(cls, 'post_hook', {})
        # already defined hooks
        for key, value in dist.get_option_dict(cmd).items():
            if key.startswith('pre_hook.'):
                pre_hook[key[9:]] = value
            elif key.startswith('post_hook.'):
                post_hook[key[9:]] = value

        # reinject local hooks
        if subparser.has_section(cmd):
            for key, value in subparser.items(cmd):
                if key.startswith('pre-hook.'):
                    pre_hook[key[9:]] = ('cardhu:setup.cfg', value)
                elif key.startswith('post-hook.'):
                    post_hook[key[9:]] = ('cardhu:setup.cfg', value)

        dist1['cmdclass'][cmd] = hook_command(cls, pre_hook, post_hook)


def hook_command(cls, pre_hook, post_hook):
    if issubclass(cls, HookedCommand):
        cls.pre_hook.update(pre_hook)
        cls.post_hook.update(post_hook)
    else:
        name = cls.__name__
        cls = type(name, (HookedCommand, cls, object), {
            'pre_hook': pre_hook, 'post_hook': post_hook
        })
    return cls


class HookedCommand(object):
    pre_hook = {}
    post_hook = {}

    def run(self):
        self.run_hook('pre_hook')
        super(HookedCommand, self).run()
        self.run_hook('post_hook')

    def run_hook(self, hookname):
        hooks = getattr(self, hookname, {})
        for alias, (src, module) in hooks.items():
            try:
                func = load(module)
            except ImportError as error:
                raise DistutilsModuleError('cannot find hook %s.%s: %s' %
                                           (hookname, alias, error))

            log.info('running %s.%s for command %s',
                     hookname, alias, self.get_command_name())
            try:
                func(self)
            except Exception as error:
                raise DistutilsError('cannot run hook %s.%s: %s' %
                                     (hookname, alias, error))

    def __getattr__(self, name):
        if name.startswith('post_hook.'):
            return self.post_hook.get(name[10:], (None, None))
        if name.startswith('pre_hook.'):
            return self.pre_hook.get(name[9:], (None, None))
        return super(HookedCommand, self).__getattr__(name)

    def __setattr__(self, name, value):
        if name.startswith('post_hook.'):
            return self.post_hook.update({name[10:]: (None, value)})
        if name.startswith('pre_hook.'):
            self.pre_hook.update({name[9:]: (None, value)})
        return super(HookedCommand, self).__setattr__(name, value)
