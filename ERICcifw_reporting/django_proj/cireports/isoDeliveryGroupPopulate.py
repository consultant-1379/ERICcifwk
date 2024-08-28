'''
Script to populate cireports_isotodeliverygroupmapping table with delivery group data related to ISO in all drops till 16.5
'''
from cireports.models import *
from datetime import datetime

def createMappingUsingComments(dropId, isoList, duplicateMapping):
    '''
    Method to create mappings using auto comment text
    '''
    isoDeliveryGroupFields = ('iso__id','deliveryGroup__id','deliveryGroup_status')
    isoDeliveryGroups = IsotoDeliveryGroupMapping.objects.all().only(isoDeliveryGroupFields).values(*isoDeliveryGroupFields)

    deliveryGroupIds = DeliverytoPackageRevMapping.objects.filter(deliveryGroup__drop__id=dropId,deliveryGroup__deleted = False).distinct().order_by('-deliveryGroup__modifiedDate').only('deliveryGroup__id').values('deliveryGroup__id')

    delGrpCommentFields = ('deliveryGroup__id','comment','date')
    delGrpComments = DeliveryGroupComment.objects.filter(deliveryGroup__id__in = deliveryGroupIds).only(delGrpCommentFields).values(*delGrpCommentFields)

    for comment in delGrpComments:
        if 'delivered this group' and 'to the drop' in comment['comment']:
            status = 'delivered'
        elif 'obsoleted this group from the drop' in comment['comment']:
            status = 'obsoleted'
        else:
            continue

        commentDate = datetime.strptime(str(comment['date']),'%Y-%m-%d %H:%M:%S')
        for i, iso in enumerate(isoList):
            endDate = datetime.strptime(str(iso['build_date']),'%Y-%m-%d %H:%M:%S')

            if i+1 == len(isoList):
                baseIsos = ISObuild.objects.only(isoFields).filter(drop__id = iso['drop__designbase__id'],mediaArtifact__testware=0).order_by('-build_date').values(*isoFields)
                if not baseIsos:
                    break
                for ind,baseIso in enumerate(baseIsos):
                    if baseIso['build_date'] >= iso['build_date']:
                        continue
                    startDate = datetime.strptime(str(baseIso['build_date']),'%Y-%m-%d %H:%M:%S')
                    break
            else:
                startDate = datetime.strptime(str(isoList[i+1]['build_date']),'%Y-%m-%d %H:%M:%S')

            if startDate < commentDate < endDate:
                isoDelGrpDict = {}
                isoDelGrpDict['iso__id'] = iso['id']
                isoDelGrpDict['deliveryGroup__id'] = comment['deliveryGroup__id']
                isoDelGrpDict['deliveryGroup_status'] = status

                if isoDelGrpDict not in isoDeliveryGroups:
                    duplicateMapping = True
                    isoDelGrpMappingObj = IsotoDeliveryGroupMapping.objects.create(iso_id=iso['id'], deliveryGroup_id=comment['deliveryGroup__id'], deliveryGroup_status=status, modifiedDate = comment['date'])
                break

    return duplicateMapping

try:
    duplicateMapping = False
    isoDeliveryGroupFields = ('iso__id','deliveryGroup__id','deliveryGroup_status')
    isoDeliveryGroups = list(IsotoDeliveryGroupMapping.objects.all().only(isoDeliveryGroupFields).values(*isoDeliveryGroupFields))

    dropFields = ('id','name','designbase__id')
    dropList = Drop.objects.only(dropFields).filter(release__product__name = 'ENM', release__name = 'ENM3.0').exclude(designbase=None).values(*dropFields).order_by('-id')

    for drop in dropList:
        isoFields = ('id','build_date','version','drop__id','drop__designbase__id')
        isoList = ISObuild.objects.filter(drop__id=drop['id'], mediaArtifact__testware=0).order_by('-build_date').only(isoFields).values(*isoFields)

        mappingFields = ('deliveryGroup__id','deliveryGroup__delivered','deliveryGroup__obsoleted','deliveryGroup__modifiedDate')
        for i, iso in enumerate(isoList):
            endDate = iso['build_date']

            if i+1 == len(isoList):
                baseIsos = ISObuild.objects.only(isoFields).filter(drop__id = iso['drop__designbase__id'],mediaArtifact__testware=0).order_by('-build_date').values(*isoFields)
                if not baseIsos:
                    break
                for ind,baseIso in enumerate(baseIsos):
                    if baseIso['build_date'] >= iso['build_date']:
                        continue
                    startDate = baseIso['build_date']
                    break
            else:
                startDate = isoList[i+1]['build_date']

            mappings = DeliverytoPackageRevMapping.objects.filter(deliveryGroup__drop__id=iso['drop__id'],deliveryGroup__deleted = False,deliveryGroup__modifiedDate__range=(startDate,endDate)).distinct().order_by('-deliveryGroup__modifiedDate').only(mappingFields).values(*mappingFields)

            for mapp in mappings:
                if mapp['deliveryGroup__delivered']:
                    status = 'delivered'
                elif mapp['deliveryGroup__obsoleted']:
                    status = 'obsoleted'
                else:
                    continue

                isoDelGrpDict = {}
                isoDelGrpDict['iso__id'] = iso['id']
                isoDelGrpDict['deliveryGroup__id'] = mapp['deliveryGroup__id']
                isoDelGrpDict['deliveryGroup_status'] = status

                if isoDelGrpDict not in isoDeliveryGroups:
                    duplicateMapping = True
                    isoDelGrpMappingObj = IsotoDeliveryGroupMapping.objects.create(iso_id=iso['id'], deliveryGroup_id=mapp['deliveryGroup__id'], deliveryGroup_status=status, modifiedDate = mapp['deliveryGroup__modifiedDate'])

        if drop['name'] == '16.5' or drop['name'] == '16.6':
            duplicateMapping = createMappingUsingComments(drop['id'],isoList,duplicateMapping)
    if duplicateMapping:
        print 'All mappings created successfully'
    else:
        print 'Mappings already exist, no new mappings created.'
except Exception as e:
    print "ERROR: creating ISO delivery group mappings: "+str(e)

