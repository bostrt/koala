from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError

class Config:
    def __init__(self, configfile):
        self.config = SafeConfigParser()
        self.config.read(configfile)

    def get_database_path(self):
        return self.get_config('database', 'path', './koala.db')
    def get_database_salt(self):
        return self.get_config('database', 'salt')

    def get_log_path(self):
        return self.get_config('log', 'path', './koala.log')
    def get_log_level(self):
        return self.get_config('log', 'level', 'WARN').upper()


    def get_config(self, section, property, default=None):
        try:
            return self.config.get(section, property)
        except (NoOptionError, NoSectionError):
            if not default:
                raise RuntimeError("Configure salt in koala.ini")
            return default

config = Config('koala.ini')
