'''
Created on 10 Jul 2012

@author: ejohmci
'''
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from ConfigParser import SafeConfigParser
from xml.etree import ElementTree
import re,os


class Command(BaseCommand):
    help = "Parse Template XML file and outputs updated XML with CIFWK Values"
    option_list = BaseCommand.option_list  + (
            make_option('--template',
                dest='template',
                help='location of template xml file'),
            )

def findWholeWord(w):
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search

        
def parseXML(self, *args, **options):
    print "Location of template:" + options['template']
    xmlInput = "django_proj/dmt/xml/multi_blade_definition_same_enclosure.xml"
    with open(xmlInput, 'rt') as file:
        tree = ElementTree.parse(file) 
        
    ElementTree.register_namespace('litp', "http://www.ericsson.com/litp")
    
    elementlist = []
    for elem in tree.iter():
        
        print(elem.tag, elem.attrib)
        elementTag = elem.tag
        
        print("Element Tag  -->  " +elementTag)
    
        elementAttr = str(elem.attrib)
        
        print("Attribute Tag  -->  " +elementAttr)
    
        if elementTag[0] == "{":
            uri, tag = elementTag[1:].split("}")
            print("ElementTag URI  -->  " + uri)
            print("ElementTag TAG  -->  " + tag)
            print("\n")
           
        if elementTag[0] != "{":
            print("Element with Tag \""+elementTag+"\" contains Data  -->  \""+elem.text+"\"")  
            if "username" in elementTag:
                elem.text = "john_mcintyre"
    
        elementlist.append(elem)
    
    xmlTreeOutput = open('django_proj/dmt/xml/cifwk_multi_blade_definition_same_enclosure.xml', 'w+')
    xmlTreeOutput.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    element = ElementTree.tostringlist(elementlist[0], 'utf-8', 'xml')
    for line in element:
        xmlTreeOutput.write(str(line))
    xmlTreeOutput.close()
#parseXML()

def parseXML2():
    print os.getcwd()
    print os.listdir(".")
    xmlInput = "django_proj/dmt/xml/sp12_multiblade_definition_same_enclosure.xml"
    with open(xmlInput, 'rt') as file:
        tree = ElementTree.parse(file) 
        
    ElementTree.register_namespace('litp', "http://www.ericsson.com/litp")
    
    parser = SafeConfigParser()
    parser.read('parseXML.ini')

  

    elementlist = []
    for elem in tree.getiterator():
        
        print(elem.tag, elem.attrib)
        elementTag = elem.tag
        
        print("Element Tag  -->  " +elementTag)
    
        elementAttr = elem.attrib
        #Nice to have if we want to change id value
        for key in sorted(elementAttr.iterkeys()):
            print "%s: %s" % (key, elementAttr[key])
            
        print("Attribute Tag  -->  " +str(elementAttr))
        
        if elementTag[0] == "{":
            uri, tag = elementTag[1:].split("}")
            print("ElementTag URI  -->  " + uri)
            print("ElementTag TAG  -->  " + tag)
            print("\n")
        
        if elementTag[0] != "{":
            print("Element with Tag \""+elementTag+"\" contains Data  -->  \""+elem.text+"\"")
            for section_name in parser.sections():
                for name, value in parser.items(section_name):
                    exist = findWholeWord(name)(elementTag) 
                    if exist != None:
                        elem.text = value
                        print("Updated Element Tag \""+elementTag+"\" contains Data  -->  \""+elem.text+"\"")
        
        elementlist.append(elem)
    
    xmlTreeOutput = open('django_proj/dmt/xml/cifwk_multi_blade_definition_same_enclosure.xml', 'w+')
    xmlTreeOutput.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    element = ElementTree.tostring(elementlist[0], 'utf-8', 'xml')
    for line in element:
        xmlTreeOutput.write(str(line))
    xmlTreeOutput.close()
    print "TEST EJOHMCI\n\n\n"
    print(ElementTree.tostring(elementlist[13], 'utf-8', 'xml'))
#parseXML2()

