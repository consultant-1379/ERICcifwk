<map version="0.9.0">
    <!-- To view this file, download free mind mapping software FreeMind from http://freemind.sourceforge.net -->
    <node CREATED="1336037971857" ID="ID_150542004" MODIFIED="1338291653716" TEXT="TORSF-17">
        <node CREATED="1336037984024" ID="ID_679454563" MODIFIED="1344426581723" POSITION="right" TEXT="Functional Tests">
            <node CREATED="1336038105179" ID="ID_404950472" MODIFIED="1340293634564" TEXT="Verify user can access injected int element ">
                <node CREATED="1336039735424" ID="ID_416732176" MODIFIED="1343821760021" TEXT="COMPONENT: ModelEventDefinitionImpl"/>
                <node CREATED="1336038744773" ID="ID_690087273" MODIFIED="1343821775514" TEXT="DESCRIPTION: Given a model event: check that the correct description is returned"/>
                <node CREATED="1336038752013" ID="ID_503780013" MODIFIED="1336038780427" TEXT="PRIORITY: HIGH"/>
                <node CREATED="1336038780830" ID="ID_1585817280" MODIFIED="1343821793831" TEXT="GROUP: acceptance"/>
                <node CREATED="1336038860069" ID="ID_248228929" MODIFIED="1343821813506" TEXT="PRE: Get a modelled event definition by calling getModeledEventDefinition"/>
                <node CREATED="1336038805518" ID="ID_1348894701" MODIFIED="1344426370196" TEXT="EXECUTE: Execute the get Description method ">
                <node CREATED="1336038832124" ID="ID_1459976699" MODIFIED="1343821893945" TEXT="VERIFY: The returned description equals the expected definition."/>
            </node>
            <node CREATED="1343821904752" ID="ID_837905808" MODIFIED="1343821908803" TEXT="VUSERS: 1"/>
            <node CREATED="1343821910148" ID="ID_1229390693" MODIFIED="1343821916252" TEXT="CONTEXT: API"/>
        </node>
        <node CREATED="1336038976371" ID="ID_1387888931" MODIFIED="1344426425250" TEXT="Verify user cannot access int element if it is not injected">
            <node CREATED="1336038752013" ID="ID_861568382" MODIFIED="1336038780427" TEXT="PRIORITY: HIGH"/>
                <node CREATED="1336038780830" ID="ID_770396001" MODIFIED="1341269062055" TEXT="GROUP: ESSENTIAL"/>
                <node CREATED="1336038860069" ID="ID_388148667" MODIFIED="1336038894941" TEXT="PRE: Service Framework properties file contains testInt property"/>
                <node CREATED="1336038805518" ID="ID_921993298" MODIFIED="1341352603437" TEXT="EXECTUTE: getTestInt ">
                    <node CREATED="1336038832124" ID="ID_932750369" MODIFIED="1341269087829" TEXT="Verify: testInt has been returned"/>
                    <node CREATED="1336038844520" ID="ID_1966741719" MODIFIED="1341269093078" TEXT="Verify: testInt value is proper"/>
                    <node CREATED="1336038851318" ID="ID_1909513528" MODIFIED="1341269096972" TEXT="Verify: response time is below 2ms"/>
                </node>
                <node CREATED="1336039735424" ID="ID_1578905422" MODIFIED="1336039756261" TEXT="COMPONENT: Injection"/>
                <node CREATED="1340293697407" ID="ID_1555454314" MODIFIED="1340293987334" TEXT="DESCRIPTION: Laasas, There is a significatnt need to do lameish laming"/>
            </node>
        </node>
        <node CREATED="1336037980751" ID="ID_353380802" MODIFIED="1336977418661" POSITION="right" TEXT="Performance Tests">
            <node CREATED="1336038105179" ID="ID_1677673059" MODIFIED="1344463957098" TEXT="Execute Verify user can access injected int element in concurrent users environment">
                <node CREATED="1336039735424" ID="ID_896241834" MODIFIED="1336039756261" TEXT="COMPONENT: Injection"/>
                <node CREATED="1340293697407" ID="ID_453656686" MODIFIED="1340293699295" TEXT="DESCRIPTION: Goal of the test case is to verify if response time and resources usage is not affected with scaling concurrent calls up to 20000"/>
                <node CREATED="1336038752013" ID="ID_433708351" MODIFIED="1340293729473" TEXT="PRIORITY: MEDIUM"/>
                <node CREATED="1336038780830" ID="ID_956157132" MODIFIED="1340293735471" TEXT="GROUP: CANFAIL"/>
                <node CREATED="1336038860069" ID="ID_239084278" MODIFIED="1336038894941" TEXT="PRE: Service Framework properties file contains testInt property"/>
                <node CREATED="1336039548353" ID="ID_1682642370" MODIFIED="1336039558008" TEXT="VUSERS: 5,100,500,1000,5000,10000,15000 "/>
                <node CREATED="1336039581466" ID="ID_1826919818" MODIFIED="1344463966946" STYLE="fork" TEXT="EXECUTE: Verify user can access injected int element">
                    <node CREATED="1336039702194" ID="ID_293437643" MODIFIED="1344463955166" TEXT="Verify: AS log has no ERROR or WARNING message"/>
                </node>
                <node CREATED="1338293029125" ID="ID_329725657" MODIFIED="1338293036781" TEXT="ATC: TORSF-18"/>
            </node>
        </node>
        <node CREATED="1336038065478" ID="ID_1299048467" MODIFIED="1343766431087" POSITION="right" TEXT="Workflow Tests"/>
        <node CREATED="1336037987873" ID="ID_1820063504" MODIFIED="1343766451965" POSITION="right" TEXT="HighAvailability Tests"/>
        <node CREATED="1343766476125" ID="ID_1303512424" MODIFIED="1343766481054" POSITION="right" TEXT="Scalability Tests"/>
        <node CREATED="1343766458099" ID="ID_1903836703" MODIFIED="1343766468545" POSITION="right" TEXT="Robustness Tests"/>
        <node CREATED="1336038009268" ID="ID_970254648" MODIFIED="1336038015456" POSITION="right" TEXT="Security Tests"/>
    </node>
</map>
