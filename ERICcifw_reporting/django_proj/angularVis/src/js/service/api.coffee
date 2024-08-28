(->

  DeploymentBaselineService = ($resource)->
    baselines:
      $resource '/api/deploymentbaseline/:type/:dropName/:groupName', type: '@type', dropName: '@dropName', groupName: '@groupName', get:
        method: 'GET'
        cache: true

    updateMaster:
      $resource '/api/deploymentbaseline/:id/change-master/', id: '@id'

    updateTaf:
      $resource '/api/deploymentbaseline/:id/change-taf/', id: '@id'

    updateComment:
      $resource '/api/deploymentbaseline/:id/change-comment/', id: '@id'

    updateAvailability:
      $resource '/api/deploymentbaseline/:id/change-availability/', id: '@id'

  DeploymentBaselineService
    .$inject = ['$resource',]

  config = ($httpProvider,$resourceProvider)->
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken'
    $httpProvider.defaults.xsrfCookieName = 'csrftoken'
    $resourceProvider.defaults.stripTrailingSlashes = false

  angular
    .module('baseline.api',['ngResource'])
    .factory('DeploymentBaselineService',DeploymentBaselineService)
    .config(config)
)()
