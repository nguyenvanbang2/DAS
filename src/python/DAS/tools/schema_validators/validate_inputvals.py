#!/usr/bin/env python
# __author__ = 'Vidmantas Zemleris'
import sys
from DAS.tools.schema_validators.json_validator import validate_mongodb_json
from DAS.tools.schema_validators.schema import Schema, And

# sample schemas
schema = Schema({'_id': {'$oid': And(basestring, len)},
                 'ts': float,
                 'value': basestring})

def main():
    """Main function"""
    if  len(sys.argv) != 2:
        print "Usage: validator <inputvals_update_file.js>"
        sys.exit(1)
    validate_mongodb_json(schema, sys.argv[1])
#
# main
#
if __name__ == '__main__':
    main()