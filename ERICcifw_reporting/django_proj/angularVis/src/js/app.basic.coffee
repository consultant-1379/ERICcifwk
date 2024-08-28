app = angular.module 'baseline.app.basic', ['baseline.api','ngRoute']

app.config ['$routeProvider','$locationProvider','$interpolateProvider', ($routeProvider,$locationProvider,$interpolateProvider) ->
    $locationProvider.html5Mode(true)
    $interpolateProvider.startSymbol('{[{')
    $interpolateProvider.endSymbol('}]}')
]

app.controller 'AppController', ['$scope','$route','$location','$routeParams','$timeout', '$compile', '$interval','$filter', 'DeploymentBaselineService', ($scope,$route,$location,$routeParams,$timeout,$compile,$interval,$filter,DeploymentBaselineService) ->

    $scope.path = $location.path()
    $scope.dropPath = $scope.path.split( "/" )
    $scope.baselines = {}
    daysOfWeek = []
    weeksOfYear = []
    $scope.overAllSlot = []
    $scope.baselineLength = 0
    $scope.itemsPerPage = 9999

    isSelected = (element) ->
      element

    $scope.showOptions = false

    $scope.toggle = ->
      $scope.showOptions = !$scope.showOptions
      return
    $scope.checkboxSelected = []

    $scope.update = ->
      $scope.count = $scope.checkboxSelected.filter(isSelected).length
      return

    $scope.checkForUpdates = ->
        $scope.deployments2 = DeploymentBaselineService.baselines.query(type: 'drop',dropName: $scope.drop)
        $scope.deployments2.$promise.then (deployments) ->
            if $scope.baselines.length == undefined && deployments.length > 0
                angular.forEach deployments, (deployment,key) ->
                    $scope.baselines[key] = deployment
                    deliveryGroup = JSON.stringify(deployment.deliveryGroup)
                    if deliveryGroup == 'null'
                        deployment.deliveryGroup = ''
                    else
                        deliveryGroupList = deployment.deliveryGroup.split(',')
                        for i in [0 .. deliveryGroupList.length-1]
                            if deliveryGroupList[i].charAt(0) != '-' && deliveryGroupList[i].charAt(1) != ''
                                deliveryGroupList[i] = '+' + deliveryGroupList[i]
                            deployment.deliveryGroup = deliveryGroupList
                    deployment.deliveryGroup.sort (software, testware) ->
                        software.length - (testware.length)
                    keys = Object.keys($scope.baselines)
                    $scope.baselineLength = keys.length
                    weeksOfYear[keys.length - 1] = $filter('date')(new Date(deployment['createdAt']), 'ww')
                    daysOfWeek[keys.length - 1] = new Date(deployment['createdAt']).getDay()
                    $scope.baselines[key].descriptionDetails = 'Wk '+ weeksOfYear[keys.length-1] + '.' + daysOfWeek[keys.length-1] + '.' + deployment['slot']
        return

    $scope.updateView = ->
        if $scope.dropPath.length == 4
            $scope.deployments = DeploymentBaselineService.baselines.query()
        else if $scope.dropPath.length == 5
            $scope.drop = $scope.dropPath[$scope.dropPath.length-2]
            $scope.deployments = DeploymentBaselineService.baselines.query(type: 'drop',dropName: $scope.drop)
        else if $scope.dropPath.length == 6
            $scope.drop = $scope.dropPath[$scope.dropPath.length-3]
            $scope.group = $scope.dropPath[$scope.dropPath.length-2]
            if $scope.group == "master"
                $scope.deployments = DeploymentBaselineService.baselines.query(type: 'dropmaster',dropName: $scope.drop)
            else
                $scope.deployments = DeploymentBaselineService.baselines.query(type: 'dropgroup',dropName: $scope.drop,groupName: $scope.group)
        $scope.checkForUpdates()

    $scope.updateView()

    $scope.showflag = false
    setTimeout (->
      $scope.$apply ->
        $scope.showflag = false
        if $scope.baselineLength == 0
            $scope.hideLoad()
            $scope.showflag = true
        return
      return
    ), 1000

    $scope.options = [
        {name: 'BUSY', value:'1'},
        {name: 'IDLE', value:'2'},
        {name: 'QUARANTINE', value:'3'},
    ];

    $scope.commentUser = 'None'
    $scope.userCommenting = false

    $scope.appendUser= (text) ->
        $scope.commentUser = text
        return

    $scope.loadingScreen = true

    $scope.hideLoad = () ->
        $timeout (->
            $scope.$apply ->
                $scope.loadingScreen = false
                return
            return
        ), 1000

    $scope.setMaster = (id,drop) ->
        $scope.updatedMaster =  DeploymentBaselineService.updateMaster.save({'id': id,'drop': drop,'master': 'true'})
        $scope.updatedMaster.$promise.then (result) ->
            $timeout ->
                $scope.updateView()

    $scope.updateTaf = (id,version) ->
        $scope.updatedTaf =  DeploymentBaselineService.updateTaf.save({'id': id,'taf': version})

    $scope.updateComment = (id, comment, index) ->
        if !comment.endsWith($scope.commentUser) && comment != ''
            comment = comment + ' - ' + $scope.commentUser
        $scope.baselines[$scope.baselineLength-index-1].comment = comment
        $scope.updatedComment = DeploymentBaselineService.updateComment.save({'id': id, 'comment': comment})

    if !String::startsWith
        String::startsWith = (searchString, position) ->
          position = position or 0
          @indexOf(searchString, position) == position

    if !String::endsWith
        String::endsWith = (pattern) ->
          d = @length - (pattern.length)
          d >= 0 and @lastIndexOf(pattern) == d

    $scope.updateAvailability = (id, availability) ->
        availability = $scope.options[availability-1]
        $scope.updatedAvailability = DeploymentBaselineService.updateAvailability.save({'id': id, 'availability': availability.name})

    $scope.cancelComment = (id, comment, index) ->
        $scope.baselines[$scope.baselineLength-index-1].comment = comment
        $scope.checkForUpdates()
]

app.filter 'orderByDrop', ->
    (items) ->
        baselines = []
        angular.forEach items, (item) ->
            baselines.push item

        baselines.sort (a,b) ->
            dropA = a.dropName.split('.')
            numberA = (parseInt(dropA[0]) * 100 ) + (parseInt(dropA[1]) * 10)
            dropB = b.dropName.split('.')
            numberB = (parseInt(dropB[0]) * 100 ) + (parseInt(dropB[1]) * 10)

            if numberA > numberB
                return -1
            if numberA < numberB
                return 1
            return 0

#Used to slice the deliverygroup items
app.filter 'slice', ->
  (arr, start, end) ->
    arr.slice start, end