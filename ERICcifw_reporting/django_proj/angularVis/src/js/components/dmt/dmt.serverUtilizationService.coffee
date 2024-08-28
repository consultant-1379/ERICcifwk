(->
  ServerUtilizationService = ($resource)->
    clusters:
      $resource '/api/deployment/clusters/',get:
        method: 'GET'
        cache: true

    groupMappings:
      $resource '/api/deployment/testgroup/mapping/',

    groups:
      $resource '/api/deployment/testgroups/',get:
        method: 'GET'
        cache: true

    latestResults:
      $resource '/api/deployment/testresults/date/:date/group/:group/', date: '@date', group: '@group',get:
        method: 'GET'
        cache: true

    results:
      $resource '/api/deployment/testresults/',get:
        method: 'GET'
        cache: true

    testcases:
      $resource '/api/deployment/testcases/',
        get:
          method: 'GET'
          cache: true

    editServerUtilisationTestcases:
      $resource '/api/deployment/testcases/:id/edit-testcase/', id: '@id'

    deleteServerUtilisationTestcases:
      $resource '/api/deployment/testcases/:id/delete-testcase/', id: '@id'




  ServerUtilizationService
    .$inject = ['$resource',]

  config = ($httpProvider,$resourceProvider)->
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken'
    $httpProvider.defaults.xsrfCookieName = 'csrftoken'
    $resourceProvider.defaults.stripTrailingSlashes = false

  angular
    .module('app.components.dmt.services',['ngResource'])
    .factory('ServerUtilizationService', ServerUtilizationService)
    .config(config)
)()
