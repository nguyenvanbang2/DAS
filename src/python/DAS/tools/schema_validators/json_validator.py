#-*- coding: ISO-8859-1 -*-
#pylint: disable=C0111,C0103
#pylint disabled: C0111(missing-docstring), C0103(invalid-name)
"""
Allows to validate files containing multiple json documents such as
the files generated by mongoexport.

Sample schemas:

.. doctest::
    inputvals = Schema({'ts': Or(float, int, long),
                        'value': basestring})

    keylearning_schema = \
        Schema(Or({'keys': [basestring, ],
                   'members': [basestring, ],
                   'system': basestring,
                   'urn': basestring},
                  {'member': basestring,
                   'stems': [basestring, ]}))

"""

import json
import pprint

from DAS.tools.schema_validators.schema import SchemaError


def validate_mongodb_json(schema, filename):
    """
    validates the given file of multiple json documents to given json schema
    (which was exported by MongoDB)

    in case of non-conformance a schema.SchemaError is thrown.
    """
    with open(filename) as file_:
        for doc in file_:
            data = json.loads(doc)
            schema.validate(data)
    return True


def validate_verbose(rules, item, print_success=False):
    """
    Validate the item to match the schema of at least one schema rule (i.e. OR)

    .. doctest::
        rules = {
                'arecord_record': Schema(arecord_record),
                'map_record': Schema(map_record),
                'presentation_record': Schema(presentation_record),
                'notation_record': Schema(notation_record)}
    """
    errors = []
    for rule_name, rule in rules.items():
        try:
            rule.validate(item)
            if print_success:
                print 'OK:', item
            break
        except SchemaError as err:
            errors.append(('rule %s failed:' % rule_name, err))
    else:
        print 'can not validate the record:'
        pprint.pprint(item)

        for err, details in errors:
            print err
            #pprint.pprint(details)
            print details
            print '------------'

        return False
    return True


def validate_file_verbose(rules, filename):
    """
    Validate the file composed of json documents to match the given rules;
    see validate_verbose() for details.
    """
    with open(filename) as file_:
        for line in file_:
            doc = json.loads(line)
            if not validate_verbose(rules, doc):
                return False
    return True
