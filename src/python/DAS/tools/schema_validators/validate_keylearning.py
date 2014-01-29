#!/usr/bin/env python
# __author__ = 'Vidmantas Zemleris'
import sys
from DAS.tools.schema_validators.json_validator import validate_mongodb_json
from DAS.tools.schema_validators.schema import Schema, And, Or


schema = \
    Schema(Or({'_id': {'$oid': And(basestring, len)},
               'keys': [basestring, ],
               'members': [basestring, ],
               'system': basestring,
               'urn': basestring},
              {'_id': {'$oid': And(basestring, len)},
               'member': basestring,
               'stems': [basestring, ]}))


def main():
    """Main function"""
    if  len(sys.argv) != 2:
        print "Usage: validator <keylearning_update_file.js>"
        sys.exit(1)
    validate_mongodb_json(schema, sys.argv[1])
#
# main
#
if __name__ == '__main__':
    main()