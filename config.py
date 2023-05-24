from configparser import ConfigParser

def get_config(configFile='ctt.ini', secretsFile='secrets.ini'):
    parser = ConfigParser()
    parser.read(configFile)
    parser.read(secretsFile)
    return parser
