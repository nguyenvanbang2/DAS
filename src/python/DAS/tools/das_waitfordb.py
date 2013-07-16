from DAS.core.das_core import DASCore
from DAS.core.das_mapping_db import DASMapping

__author__ = 'vidma'

import sys, time
from DAS.utils.das_config import das_readconfig
from DAS.utils.das_db import db_connection, is_db_alive


def check_mappings_readiness():
    config = das_readconfig()
    # TODO: check if the mappings in DB are consistent

    print('db alive. checking it\'s state...')
    try:
        #dascore = DASCore()
        dasmapping = DASMapping(config)
        if dasmapping.check_maps():
            return True
    except Exception, e:
        print e

    print 'no DAS mappings present...'
    return False


def on_db_available():
    print 'DB is available'

    if check_mappings_readiness():
        print('Mappings seem to be fine...\n'
              'just in case, wait 10s until the mappings are fully loaded...')
        time.sleep(10)
        sys.exit(0)

def db_monitor(uri, func, sleep=5, max_retries=None):
    """
    Check status of MongoDB connection. Invoke provided function upon
    successfull connection.
    """
    conn = None
    retries = 0
    while True:
        # db is dead
        if not (conn and is_db_alive(uri)):
            try:
                conn = db_connection(uri)
            except Exception, e:
                print e

        if conn and is_db_alive(uri):
            print "### established connection %s" % conn
            func()

        # limit the number of retries if needed
        retries += 1
        if max_retries is not None and retries > max_retries:
            break

        time.sleep(sleep)


def waitfordb(max_time):
    """
    waits until DB is ready as well as until DAS mappings are created/updated.
    """
    config = das_readconfig()
    dburi = config['mongodb']['dburi']
    sleep_time=5
    db_monitor(dburi, on_db_available,
               sleep=sleep_time, max_retries=max_time // sleep_time)

    print 'DB is not available and the timeout has passed'
    sys.exit(-1)

def test():
    # remove mappings
    # shall fail

    # stop db
    # restart it - shall work
    pass


if __name__ == '__main__':
    waitfordb(60)