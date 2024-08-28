<map version="0.9.0">
<!-- To view this file, download free mind mapping software FreeMind from http://freemind.sourceforge.net -->
<node CREATED="1336037971857" ID="ID_150542004" MODIFIED="1341408249942" TEXT="TT-60">
<node CREATED="1336037984024" ID="ID_679454563" MODIFIED="1336038022662" POSITION="right" TEXT="Feature Tests">
<node CREATED="1336038105179" ID="ID_404950472" MODIFIED="1341408183950" TEXT="Verify that the TOR PMS service can complete an Simple File Transfer (Ftp) using the Mediation Service to collect and store the file to a default destination, notification is received on fileCollectionQueue in PMService.">
<node CREATED="1336039735424" ID="ID_416732176" MODIFIED="1341408631734" TEXT="COMPONENT: Injection"/>
<node CREATED="1336038744773" ID="ID_690087273" MODIFIED="1341408604237" TEXT="DESCRIPTION: Verify that the TOR PMS service can complete an Simple File Transfer (Ftp) using the Mediation Service to collect and store the file to a default destination and that notification of successful transfer is received on JMS queue.&#xa;Standard FTP, file renaming,  multiple files in directory, logical FDN(Fully Defined Name)."/>
<node CREATED="1336038752013" ID="ID_503780013" MODIFIED="1336038780427" TEXT="PRIORITY: HIGH"/>
<node CREATED="1336038780830" ID="ID_1585817280" MODIFIED="1336038803532" TEXT="GROUP: ESSENTIAL"/>
<node CREATED="1336038860069" ID="ID_248228929" MODIFIED="1341408676399" TEXT="PRE: NETSIM FTP Server is available, Application Server ready to receive PMS transfer requests and replies.  "/>
<node CREATED="1336038805518" FOLDED="true" ID="ID_1348894701" MODIFIED="1341407860790" TEXT="Place Test File (file1.txt)  to be transferred in appropriate Target Path">
<node CREATED="1336038832124" ID="ID_1459976699" MODIFIED="1337006480830" TEXT="File is now ready for transfer "/>
</node>
<node CREATED="1336038805518" ID="ID_694477303" MODIFIED="1337006527830" TEXT="Create PM File Transfer Request Event and Verify Result ">
<node CREATED="1336038832124" ID="ID_909391777" MODIFIED="1337007841990" TEXT="Modelled Event is received on S-FWK Event Bus  "/>
<node CREATED="1337007863795" ID="ID_916072340" MODIFIED="1337008197561" TEXT="Modelled Event with Mediation Task Request is sent to the Mediation Client "/>
<node CREATED="1337008142045" ID="ID_741192226" MODIFIED="1337008684389" TEXT="Mediation Implementation completes the File Transfer to prefefined local directory"/>
<node CREATED="1337008689728" ID="ID_427902219" MODIFIED="1337008741947" TEXT="Confirm file exists in local directory and has correct file name and file contents"/>
<node CREATED="1337008744858" ID="ID_1206478664" MODIFIED="1337008817829" TEXT="Confirm source file is still present in the &quot;remote&quot; location"/>
<node CREATED="1341408701282" ID="ID_1531661003" MODIFIED="1341417925373" TEXT="Confirm that notification is received with correct job ID and number of byte transfered and bytes stored"/>
</node>
</node>
</node>
<node CREATED="1336038065478" ID="ID_1299048467" MODIFIED="1336990235950" POSITION="right" TEXT="Integration Tests"/>
<node CREATED="1336037987873" ID="ID_1820063504" MODIFIED="1336039264047" POSITION="right" TEXT="Load Tests"/>
<node CREATED="1336037980751" ID="ID_353380802" MODIFIED="1336990215979" POSITION="right" TEXT="Performance Tests"/>
<node CREATED="1336038009268" ID="ID_970254648" MODIFIED="1336038015456" POSITION="right" TEXT="Security Tests"/>
</node>
</map>
