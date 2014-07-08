from distutils import log

def setup_hook(config):
    """Filter config parsed from a setup.cfg to inject our defaults."""
    log.info('setup_hook %s', config)
