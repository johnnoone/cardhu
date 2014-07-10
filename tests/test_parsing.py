from unittest import TestCase
from cardhu.parsing import ConfigParser, read_keyval
from textwrap import dedent
import os.path

here = os.path.abspath(os.path.dirname(__file__))

def field(data):
    return dedent(str(data).strip('\n')).strip()


class Parsing(TestCase):
    def test_multi(self):
        parser = ConfigParser()
        parser.read(os.path.join(here, 'config.cfg'))
        value = parser.get('multi', 'package_data')
        assert value == field("""
    packagename = pattern1 pattern2 pattern3 ; lol
    packagename.subpack = # back
        pattern1
        pattern2
        pattern3

        """)
        value = parser.getmulti('multi', 'package_data')
        assert value == [
            'packagename = pattern1 pattern2 pattern3 ; lol',
            'packagename.subpack = # back',
            '    pattern1',
            '    pattern2',
            '    pattern3'
        ]

    def test_keyval(self):
        assert read_keyval('foo') == (None, None)
        assert read_keyval('foo = bar') == ('foo', 'bar')
        assert read_keyval('foo = ') == ('foo', None)
        assert read_keyval('foo >= bar = baz') == ('foo >= bar', 'baz')
        assert read_keyval('foo = bar >= baz') == ('foo', 'bar >= baz')
        assert read_keyval('reST = docutils >= 0.3') == ('reST', 'docutils >= 0.3')
