"""
    Cardhu config parser
    ~~~~~~~~~~~~~~~~~~~~

"""

__all__ = ['ConfigParser']

try:
    from configparser import SafeConfigParser, NoOptionError, NoSectionError, ParsingError
except ImportError:
    from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError, ParsingError

import logging
import re
from collections import defaultdict, OrderedDict
from textwrap import dedent

logger = logging.getLogger(__name__)


class ConfigParser(object):
    comments_marker = ('#', ';')
    comment_line = re.compile('^\s*(#|;)\s*(?P<comment>.+)').match

    def __init__(self, defaults=None, tab_indent=4):
        """
        :param dict defaults: defaults values
        :param int tab_indent: set the conversion from tabs to spaces
        """
        self.tab_indent = tab_indent
        self._defaults = defaults or {}
        self._sections = defaultdict(OrderedDict)
        self._user = defaultdict(OrderedDict)

    def read(self, filename):
        with open(filename, 'r') as file:
            contents = file.read()

        return self._read(contents)

    def _read(self, contents):
        print(contents)
        data = defaultdict(OrderedDict)

        section = None
        options = None
        option_name, option_value = None, None

        spaces = ' ' * self.tab_indent
        def clean(line):
            line = line.replace('\t', spaces)
            return line

        for i, line in enumerate(contents.splitlines(False)):
            line = clean(line)
            comment = self.comment_line(line)
            if comment:
                logger.debug('got comment', comment.group('comment'))
                continue
            elif not line:
                continue
            elif line.startswith('[') and line.strip().endswith(']'):
                section = line.strip()[1:-1]
                options = data[section]
                continue
            elif line and line[0] != ' ':
                # an option_name?
                tmp = line.strip()
                if tmp.endswith('='):
                    # an open option
                    option_name = tmp[:-1].strip()
                    option_value = WaitingValue(section, option_name)
                    options[option_name] = option_value
                    continue
                elif '=' in tmp:
                    # a self clausing option
                    option_name, _, option_value = tmp.partition('=')
                    options[option_name.strip()] = InlinedValue(section,
                                                                option_name,
                                                                option_value.strip())
                    continue
            elif isinstance(option_value, WaitingValue):
                # a waiting value!
                option_value = MultilineValue(section,
                                              option_name,
                                              line)
                options[option_name] = option_value
                continue
            elif isinstance(option_value, MultilineValue):
                # a multiline value
                option_value.value += '\n' + line
                continue
            else:
                raise ParsingError(repr(line), i, option_value)

        # and now resolve data
        response = defaultdict(OrderedDict)
        for section, options in data.items():
            opts = response[section]
            for name, value in options.items():
                opts[name] = value.resolve()

        return self._sections.update(response)

    def defaults(self):
        return dict(self._defaults)

    def has_option(self, section, option):
        """docstring for get"""
        try:
            self.get(section, option)
        except NoOptionError:
            return False
        return True

    def has_section(self, section):
        for provider in (self._user, self._sections, self._defaults):
            if section in provider:
                return True
        return False

    def sections(self):
        """docstring for sections"""
        merged = set()
        for provider in (self._user, self._sections, self._defaults):
            merged.update(provider.keys())
        return sorted(merged)

    def options(self, section):
        merged = set()
        defined = False
        for provider in (self._user, self._sections, self._defaults):
            try:
                merged.update(provider[section].keys())
                defined = True
            except KeyError:
                pass
        if not defined:
            raise NoSectionError('section {} is not defined'.format(section))
        return sorted(merged)

    def items(self, section):
        merged = dict()
        defined = False
        for provider in (self._defaults, self._sections, self._user):
            try:
                merged.update(provider[section])
                defined = True
            except KeyError:
                pass
        if not defined:
            raise NoSectionError('section {} is not defined'.format(section))
        return merged.items()

    def get(self, section, option):
        """
        Get an option value for the named section.
        """
        for provider in (self._user, self._sections, self._defaults):
            try:
                return provider[section][option]
            except KeyError:
                pass
        raise NoOptionError(option, section)

    def getint(self, section, option):
        """
        A convenience method which coerces the option in the specified section
        to an integer.
        """
        return int(self.get(section, option))

    def getfloat(self, section, option):
        """
        A convenience method which coerces the option in the specified section
        to a floating point number.
        """
        return float(self.get(section, option))

    def getboolean(self, section, option):
        """
        A convenience method which coerces the option in the specified section
        to a floating point number.
        """
        value = self.get(section, option)
        if str(value).lower() in ('1', 'yes', 'true', "on"):
            return True
        if str(value).lower() in ('0', 'no', 'false', 'off'):
            return False
        raise ValueError('cannot use it as a boolean value')

    def getmulti(self, section, option):
        """
        A convenience method which coerces the option in the specified section
        to a list value.

        for example, this configuration file::

            [section]
            foo =
                bar
                baz

        will be parsed has::

            assert parser.getmulti('section', 'foo') == ['bar', 'baz']

        """
        data = self.get(section, option)
        if '\n' not in data and '=' not in data:
            # oneliner version
            return data.strip().split()
        # nested version
        return [element.strip() for element in data.strip().split('\n')]

    def getfile(self, section, option):
        """
        A convenience method which loads the content of option.
        """
        with open(self.get(section, option), 'r') as file:
            return file.read()

    def getcsv(self, section, option):
        """
        A convenience method which coerces the option in the specified section
        to a list value.

        for example, this configuration file::

            [section]
            foo = bar, baz quux
            quux = bar baz

        will be parsed has::

            assert parser.getcsv('section', 'foo') == ['bar', 'baz quux']
            assert parser.getcsv('section', 'quux') == ['bar', 'baz']
        """
        elements = self.get(section, option)
        splitter = ',' if ',' in elements else None
        return [element.strip() for element in elements.split(splitter)]


class InlinedValue(object):
    def __init__(self, section, key, value):
        self.section = section
        self.key = key
        self.value = value

    def resolve(self):
        return self.value


class MultilineValue(object):
    def __init__(self, section, key, value):
        self.section = section
        self.key = key
        self.value = value

    def resolve(self):
        value = dedent(self.value)
        if value and value.startswith(' '):
            msg = 'Mixed indentations levels in {}:{}:\n{!r}'
            raise ValueError(msg.format(self.section, self.key, value))
        return value

    def __str__(self):
        return '{}'.format(self.value)

    def __repr__(self):
        return '{!r}'.format(self.value)


class WaitingValue(object):
    def __init__(self, section, key):
        self.section = section
        self.key = key

    def resolve(self):
        return None
