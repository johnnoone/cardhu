from distutils import log


def setup_hook(config):
    """Filter config parsed from a setup.cfg to inject our defaults."""
    log.info('setup_hook %s', config)


def pre_develop(cmd):
    log.info('pre_develop hook %s', cmd.get_command_name())


def pre_install(cmd):
    log.info('pre_install hook %s', cmd.get_command_name())
