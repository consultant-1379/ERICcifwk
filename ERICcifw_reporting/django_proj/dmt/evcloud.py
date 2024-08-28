from libcloud.compute.drivers.vcloud import *
import logging
from ciconfig import CIConfig

logger = logging.getLogger(__name__)
config = CIConfig()

class EVCloudNodeDriver(VCloud_1_5_NodeDriver):
    def reset_mac(self, node, vm, nicid):
        logger.info("Extenstion of API in reset_mac")
        nodes = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc.id)
            elms = res.object.findall(fixxpath(
                res.object, "ResourceEntities/ResourceEntity")
            )
            vapps = [
                (i.get('name'), get_url_path(i.get('href')))
                for i in elms
                if i.get('type')
                    == 'application/vnd.vmware.vcloud.vApp+xml'
                    and i.get('name')
            ]

            for vapp_name, vapp_href in vapps:
                logger.debug("VAPP: " + vapp_name)
                res = self.connection.request(
                    vapp_href,
                    headers={'Content-Type': 'application/vnd.vmware.vcloud.vApp+xml'}
                )
                if vapp_name == node:
                    # TODO: Clean up so we can pass a specific MAC, interface or combo thereof
                    self._change_vm_mac(res.object.get('href'), vm, "THIS IS NOT VALID")
                    return

    def _change_vm_mac(self, vapp_or_vm_id, vm_name, macaddr):
        logger.info("Extenstion of API in _change_vm_mac")
        if macaddr is None:
            macaddr = ""

        vms = self._get_vm_elements(vapp_or_vm_id)

        for vm in vms:
            if vm.get('name') == vm_name:
                res = self.connection.request(
                        '%s/networkConnectionSection' % get_url_path(vm.get('href'))
                        )
                net_conns = res.object.findall(fixxpath(res.object, 'NetworkConnection'))
                for c in net_conns:
                    if c.find(fixxpath(c, 'MACAddress')).text is not None:
                        # DIRTY HACK: need to abstract this out elsewhere
                        if str(c.find(fixxpath(c, 'MACAddress')).text) == "00:50:56:00:00:01":
                            logger.info("Not changing eth1 from " + c.find(fixxpath(c, 'MACAddress')).text)
                            continue
                        else:
                            logger.info("changing to " + macaddr + " from " + c.find(fixxpath(c, 'MACAddress')).text)
                    else:
                        logger.info("changing to " + macaddr + " from None Object")
                    #c.find(fixxpath(c, 'MACAddress')).text = macaddr
                    c.remove(c.find(fixxpath(c, 'MACAddress')))

                res = self.connection.request('%s/networkConnectionSection' % get_url_path(vm.get('href')),
                                              data=ET.tostring(res.object),
                                              method='PUT',
                                              headers={'Content-Type':
                                                       'application/vnd.vmware.vcloud.networkConnectionSection+xml'}
                )
                self._wait_for_task_completion(res.object.get('href'))
                return


