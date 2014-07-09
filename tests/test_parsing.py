from unittest import TestCase
from cardhu.parsing import ConfigParser
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
            'pattern1',
            'pattern2',
            'pattern3'
        ]