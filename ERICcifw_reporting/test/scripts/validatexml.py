#!/usr/bin/python

from lxml import etree
import sys

print "Parsing " + sys.argv[2] + " using " + sys.argv[1]
parser = etree.XMLParser(dtd_validation=True)
schema_root = etree.XML(open(sys.argv[1]).read())
schema = etree.XMLSchema(schema_root)
parser = etree.XMLParser(schema=schema)
mydef = etree.fromstring(open(sys.argv[2]).read(), parser)
