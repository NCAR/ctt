from .casper import Casper
from .shasta import Derecho, Gust

def get_cluster(conf):
    """Takes a system full or short name and returns an object representing that system"""
    name = conf["name"].lower()
    if name == "casper" or name == "cr":
        return Casper(conf)
    if name == "gust" or name == "gu":
        return Gust(conf)
    if name == "derecho" or name == "de":
        return Derecho(conf)



