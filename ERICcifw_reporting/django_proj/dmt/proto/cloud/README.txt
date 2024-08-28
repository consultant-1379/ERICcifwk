On Your Server
mkdir /export/scripts/
mount atmgtvm3.athtem.eei.ericsson.se:/export/scripts /export/scripts

You'll be mounted as read only.

So I have put together a fair few of the common functions we will need from the API, in a java jar, and written a shell wrapper around that. That wrapper script is located here

/export/scripts/CLOUD/bin/vCloudFunctions.sh

So we run it giving arguments username, password, organization we are in, and a function name. Each function obviously will need different arguments. Below should be the commands you requested.

Deploying From Catalog (This function outputs the id of the newly created vapp)
/export/scripts/CLOUD/bin/vCloudFunctions.sh --username ciuser --password ciuser01 --organization Misc -f deploy_from_catalog --destorgvdcname Misc_vDC --vapptemplateid <the id of your vapp template> --newvappname "<a vapp name of your choosing>" --linkedclone true

Update the Org Network On The Gateway (Only really necessary if deploying from a catalog that.s in a different organization, but no harm in putting it in as a step in any case, it won't do any harm)
/export/scripts/CLOUD/bin/vCloudFunctions.sh --username ciuser --password ciuser01 --organization Misc -f update_org_network_gateway --vappid <vapp id>

Reset the mac on the gateway
/export/scripts/CLOUD/bin/vCloudFunctions.sh --username ciuser --password ciuser01 --organization Misc -f reset_mac_gateway --vappid <vapp id>

Power on the gateway (This function waits until the gateway boots, and gets an IP. It returns the IP address then as output)
/export/scripts/CLOUD/bin/vCloudFunctions.sh --username ciuser --password ciuser01 --organization Misc -f poweron_gateway --vappid <vapp id>

Start the vapp
/export/scripts/CLOUD/bin/vCloudFunctions.sh --username ciuser --password ciuser01 --organization Misc -f start_vapp --vappid <vapp id>



Function to list vapps

-f list_vapps_in_org --orgname Misc

Function to list vapp templates

-f list_vapp_templates_in_org --orgname Misc


I have completed the function to add a vapp to a catalog. It seems to work fine from my end. Can you double check if its OK for you.

-f add_vapp_to_catalog --vappid urn:vcloud:vapp:39da1fba-0376-48f3-97bd-baeb2d1297d5 --newvapptemplatename "New catalog item" --destcatalogname Misc_Catalog
NEWVAPPTEMPLATEID urn:vcloud:vapptemplate:c20e0e9d-94fe-47f6-a55c-57015eb3fae8



I got a chance to put together the function get the list of nics on a vm. I have it outputting the same information that.s presented in the vCloud gui, ie

NIC# <colon> ISCONNECTED <colon> NETWORK_NAME <colon> IP_ALLOCATION_TYPE <Colon> IP_ADDRESS <colon> MAC_ADDRESS

Eg

 -f list_nics_on_vm --vmid urn:vcloud:vm:c7ff966b-dddd-4814-a763-b4c71cbf84da
 0;true;Build-Ext-vts1;DHCP;10.45.200.99;00:50:56:01:02:a7
 1;true;build_network_pool;DHCP;;00:50:56:00:00:01

 Let me know if that.s OK for your need to get the IP addresses for a vm.

Also theres now 3 functions to get the catalog name, org name and orgvdc name of a vapp template in a catalog as requested.

-f get_catalog_of_vapp_template --vapptemplateid <vapptemplateid>
-f get_org_of_vapp_template --vapptemplateid <vapptemplateid>
-f get_orgvdc_of_vapp_template --vapptemplateid <vapptemplateid>
