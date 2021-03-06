cardhu
======

Extends setupools_ in order to parse Distutils2_ setup.cfg, pip requirements file ...
This project is largely inspired by the d2to1_ library.

Usage
-----


In your setup.py, the only requirement is::

    from setuptools import setup

    setup(
        setup_requires=['cardhu'],
        cardhu=True
    )

Allows you to use a Distutils2_ setup.cfg like configuration file::

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

This lib also allows to hook your setuptools commands::

    # local hook
    [install]

    pre-hook.cardhu = cardhu.hooks.pre_install
    post-hook.cardhu = cardhu.hooks.pre_install

    # global hook
    [entry_points]

    cardhu.pre_hooks =
      install = cardhu.hooks:pre_install
      develop = cardhu.hooks:pre_develop



This lib expose more features, for example, the development requirements will be automatically installed when using ``python setup.py develop``::

    [metadata]
    requires-dev =
      docutils >= 0.3

Or the same before running a test::

    [metadata]
    requires-test =
        py.test


Implementation
--------------

**Goals:**

-   Implement the full Distutils2_ `setup.cfg`_ files
-   Implement the Distutils2_ resources, based on the `sysconfig module`_.
-   Make ``python setup.py (develop|install|tests)`` more easy, by loading
    requirements files::

    1.  requirements-{dev|test}-{target_version}.txt
    2.  requirements-{dev|test}.txt
    3.  requirements.txt
-   extends the -r keyword to git and mercurial in order to create the last revision number (https://pythonhosted.org/setuptools/setuptools.html#tagging-and-daily-build-or-snapshot-releases)
-   Automate changelog.rst and authors.rst files completion.

**Incompatibilities:**

-   Options with `environment markers`_ are not implemented yet.


**Currently implemented:**

-   some of the distutils2 keywords
-   ``entry_points`` backport from distutils::

        [entry_points]
        distutils.setup_keywords =
          cardhu = cardhu.core:cardhu

-   setup(cardhu=True) will loads distutils2 setup.cfg parts
-   Command hooks: https://pythonhosted.org/Distutils2/distutils/commandhooks.html::

        # file: myhooks.py
        def my_install_hook(install_cmd):
            print("Oh la la! Someone is installing my project!")
    
    ::

        [install]
        pre-hook.project = myhooks.my_install_hook

-   Custom ConfigParser, in order to play well with multi values.

-   Distutils2_ do not support extra_require keyword (https://pythonhosted.org/setuptools/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies), so added this under::

        [metadata]
        requires-extra =
          reST = docutils >= 0.3
          python_version >= "2.7" =
            six
            foo


Distutils2
----------

    see http://alexis.notmyidea.org/distutils2/setupcfg.html, Distutils2_


Pip and wheels
--------------

    see ...


.. _Distutils2: https://pythonhosted.org/Distutils2/distutils/commandhooks.html
.. _`environment markers`: http://legacy.python.org/dev/peps/pep-0345/#environment-markers
.. _`setup.cfg`: http://alexis.notmyidea.org/distutils2/setupcfg.html
.. _d2to1: https://pypi.python.org/pypi/d2to1
.. _setupools: https://pythonhosted.org/setuptools/setuptools.html
.. _`sysconfig module`: https://docs.python.org/3.4/library/sysconfig.html