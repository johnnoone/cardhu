cardhu
======

Setup tools extension, that can talks distutils2 setup.cfg, pip requirements file ...


Goals:

    - use distutils2 setup.cfg files
    - python setup.py install will find and use the first of these files:
        1. requirements-{target_version}.txt
        2. requirements.txt
    - python setup.py develop will find and use the first of these files:
        1. requirements-dev-{target_version}.txt
        2. requirements-dev.txt
    - python setup.py test will find and use the first of these files:
        1. requirements-test-{target_version}.txt
        2. requirements-test.txt
    - extends the -r keyword to git and mercurial in order to create the last revision number (https://pythonhosted.org/setuptools/setuptools.html#tagging-and-daily-build-or-snapshot-releases)

Incompatibilities:

    - distutils2 do not support extra_require keyword (https://pythonhosted.org/setuptools/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies)


Usage
-----


In your setup.py, the only requirement is::

    from setuptools import setup

    setup(
        setup_requires=['cardhu'],
        cardhu=True
    )

And then your setup.cfg must be like this::

    [metadata]
    name = cardhu
    version = 0.1.1
    author = Xavier Barbosa
    summary = Allows using distutils2-like setup.cfg files for a package's metadata
     with a distribute/setuptools setup.py
    keywords =
        setup
        distutils
    [files]
    packages = cardhu


Distutils2
----------

    see http://alexis.notmyidea.org/distutils2/setupcfg.html


Pip and wheels
--------------

    see ...
