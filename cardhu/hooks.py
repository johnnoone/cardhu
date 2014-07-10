from distutils import log


def setup_hook(config):
    """Filter config parsed from a setup.cfg to inject our defaults."""
    log.info('setup_hook %s', config)


def pre_develop(cmd):
    """
    On ``python setup.py develop``, installs dist.dev_requires packages
    """
    log.info('pre_develop hook %s', cmd.get_command_name())
    if not getattr(cmd, 'uninstall', False):
        dist = cmd.distribution
        if dist.install_requires:
            log.info('install run requires')
            dist.fetch_build_eggs(dist.install_requires)
        if getattr(dist, 'dev_requires'):
            log.info('install development requires')
            dist.fetch_build_eggs(dist.dev_requires)


def pre_install(cmd):
    log.info('pre_install hook %s', cmd.get_command_name())
