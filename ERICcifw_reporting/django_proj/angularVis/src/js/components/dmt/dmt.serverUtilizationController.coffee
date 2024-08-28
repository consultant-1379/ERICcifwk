(->
  UtilizationController = (DeploymentBaselineService,ServerUtilizationService,$filter,$modal,OrderByPercentFilter)->

      init = ()=>
          @testcaseDescriptions = {}
          @summaryResults = {}
          @overallResults = {}
          @clusters = []
          @groups = []
          @groupMappings = {}
          @curDate = null
          @noData = false
          @failureCounts = 0
          @totalServers = 0
          @defaultGroup = null
          @showDivs = {'checks': false,'groups': false,'mappings':false,'filter':false}
          @showMsgs = {'checks': false,'groups': false,'mappings':false,'filter':false}
          @checkMsg = null
          @groupMsg = null
          @mapMsg = null
          date = new Date()
          @curDate = $filter('date')(new Date(), 'dd-MM-yyyy')
          populateTestcases()
          populateGroups()
          populateGroupMappings()
          populateClusters()

      populateTestcases = ()=>
        ServerUtilizationService
          .testcases
          .query()
          .$promise.then (data) =>
            angular.forEach data, (testcaseDesc) =>
              @testcaseDescriptions[testcaseDesc.id] = testcaseDesc

      populateGroups = ()=>
        ServerUtilizationService
          .groups
          .query()
          .$promise.then (data) =>
            angular.forEach data, (group) =>
              if group['defaultGroup'] == true
                @defaultGroup = group['testGroup']
              @groups.push(group)
            latestResults()

      populateClusters = ()=>
        ServerUtilizationService
          .clusters
          .query()
          .$promise.then (data) =>
            angular.forEach data, (cluster) =>
              @clusters.push(cluster)

      populateGroupMappings = ()=>
        ServerUtilizationService
          .groupMappings
          .query()
          .$promise.then (data) =>
            angular.forEach data, (groupMapping) =>
              @groupMappings[Object.keys(@groupMappings).length] = groupMapping

      latestResults = ()=>
        ServerUtilizationService
          .latestResults
          .query(date: @curDate,group: @defaultGroup)
          .$promise.then (data) =>
            angular.forEach data, (testResults) =>
              keepGoing = true
              if @summaryResults[testResults.clusterName] == undefined
                id = testResults.clusterName.split(' ')[0]
                @summaryResults[testResults.clusterName] = [{"id": id,"success": 0,"total": 0,"percent": 0,"recentAutodeploy":false}]
              angular.forEach @summaryResults[testResults.clusterName], (cluster)=>
                if testResults.testcase_description is cluster.testcase_description
                  keepGoing = false
              if keepGoing
                @summaryResults[testResults.clusterName].push(testResults)
                @summaryResults[testResults.clusterName].jobRan = false
                if testResults.result == true
                  @summaryResults[testResults.clusterName][0].success += 1
                @summaryResults[testResults.clusterName][0].total += 1
                @summaryResults[testResults.clusterName][0].percent = (@summaryResults[testResults.clusterName][0].success / @summaryResults[testResults.clusterName][0].total) * 100
            if Object.keys(@summaryResults).length == 0
               @noData = true
            getBaselineInfo()

      getBaselineInfo = ()=>
        totalUpdated = false
        DeploymentBaselineService
          .baselines
          .query().$promise.then (data) =>
            angular.forEach data, (testResults) =>
              if testResults.clusterName of @summaryResults
                @summaryResults[testResults.clusterName].jobRan = true
                testDate = new Date(testResults.createdAt)
                date = new Date()
                weekAgoSeconds = date.getTime() - (7 * 24 * 60 * 60 * 1000)
                date.setTime(weekAgoSeconds)
                result = false
                if testDate > date
                  result = true
                  if result == true
                    @summaryResults[testResults.clusterName][0].recentAutodeploy = true
                testDate = $filter('date')(new Date(testResults.createdAt), 'dd-MM-yyyy')
                @summaryResults[testResults.clusterName].jobInfo = {date: testDate, details: testResults.descriptionDetails,result: result}
            angular.forEach @summaryResults, (value) =>
              if value[0].recentAutodeploy
                value[0].success += 1
              value[0].total += 1
              value[0].percent = (value[0].success / value[0].total) * 100


      @addTestcase = (desc,testcase,enabled) =>
        data = {'testcase_description': desc, 'testcase': testcase, 'enabled': enabled}
        ServerUtilizationService
            .testcases
            .save(data)
            .$promise.then ((data)=>
              @testcaseDescriptions[Object.keys(@testcaseDescriptions).length] = data
              @showMsgs['checks'] = true
              @checkMsg = "Check added successfully"
            ), =>
              @showMsgs['checks'] = true
              @checkMsg = "Error check inputs and login"


      @addGroup = (groupName) =>
        data = {'testGroup': groupName}
        ServerUtilizationService
            .groups
            .save(data)
            .$promise.then ((data)=>
              @groups[Object.keys(@groups).length] = data
              @showMsgs['groups'] = true
              @groupMsg = "Group added successfully"
            ), =>
              @showMsgs['groups'] = true
              @groupMsg = "Error check inputs and login"

      @addMapping = (groupMapName,clusterName) =>
        cluster = clusterName.name
        groupName = groupMapName.testGroup
        data = {'cluster': cluster,'group': groupName}
        ServerUtilizationService
            .groupMappings
            .save(data)
            .$promise.then ((data)=>
              @groupMappings[Object.keys(@groupMappings).length] = data
              @showMsgs['mappings'] = true
              @mapMsg = "Mapping added successfully"
            ), =>
              @showMsgs['mappings'] = true
              @mapMsg = "Error with request check login details"

      @checkFilter = (input) =>
        angular.forEach @showDivs, (key, value) =>
          if input == value
            if @showDivs[value] == true
              @showDivs[value] = false
              @showMsgs[value] = false
            else
              @showDivs[value] = true
          else
            @showDivs[value] = false


      @updateFilterGroup = (groupName) =>
        @defaultGroup = groupName['testGroup']
        @summaryResults = {}
        @noData = false
        latestResults()
      
      @editServerUtilisationCheck = (id,description,checks,enabled) ->
        modalInstance = $modal.open(
          templateUrl: 'static/editServerUtilisationCheck.html'
          controller: 'EditModalCtrl as edit'
          windowClass: 'center-modal'
          resolve:
              id: -> id
              description: -> description
              testcase: -> checks
              enabled: -> enabled
        )
        modalInstance.result.then((data) =>
          @testcaseDescriptions[data.id] = data
          return
        )
      @deleteServerUtilisationCheck = (id,description,checks,enabled) ->
        modalInstance = $modal.open(
          templateUrl: 'static/deleteServerUtilisationCheck.html'
          controller: 'EditModalCtrl as edit'
          windowClass: 'center-modal'
          resolve:
              id: -> id
              description: -> description
              testcase: -> checks
              enabled: -> enabled
        )
        modalInstance.result.then((data) =>
          delete @testcaseDescriptions[data.id]
          return
        )
      @cancel = ->

      init()

      return
  
  EditModalCtrl = (ServerUtilizationService,$modalInstance,id,description,testcase,enabled)->
    @id = id
    @description = description
    @testcase = testcase
    @enabled = enabled

    @ok = (id,desc,testcase,enabled) =>
      data = {'id': id, 'testcase_description': desc, 'testcase': testcase, 'enabled': enabled}
      ServerUtilizationService
          .editServerUtilisationTestcases
          .save(data)
          .$promise.then ((data)=>
              $modalInstance.close(data)
            )
      return

    @okDelete = (id) =>
      data = {'id': id}
      ServerUtilizationService
          .deleteServerUtilisationTestcases
          .save(data)
          .$promise.then ((data)=>
            $modalInstance.close(data)
          )
      return

    @cancel = ->
      $modalInstance.dismiss 'cancel'
      return
    return

  config = ($locationProvider,$interpolateProvider,$httpProvider)->
    $locationProvider.html5Mode(true)
    $interpolateProvider.startSymbol('{[{')
    $interpolateProvider.endSymbol('}]}')
    $httpProvider.defaults.headers.common['X-CSRFToken'] = $('input[name=csrfmiddlewaretoken]').val()
    $httpProvider.defaults.headers.post['X-CSRFToken'] = $('input[name=csrfmiddlewaretoken]').val()

  UtilizationController
      .$inject = ['DeploymentBaselineService','ServerUtilizationService','$filter','$modal']
      
  angular
      .module('app.components.dmt')
      .controller('UtilizationController',UtilizationController)
      .controller('EditModalCtrl',EditModalCtrl)
      .config(config)
)()
