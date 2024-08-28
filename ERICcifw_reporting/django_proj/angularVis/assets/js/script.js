(function() {
  var app;

  app = angular.module('baseline.app.basic', []);

  app.controller('AppController', [
    '$scope', '$http', function($scope, $http) {
      $scope.baselines = [];
      return $http.get('/api/baselines').then(function(result) {
        return angular.forEach(result.data, function(item) {
          return $scope.baselines.push(item);
        });
      });
    }
  ]);

}).call(this);

(function() {
  var app;

  app = angular.module('baseline.app.resource', ['baseline.api']);

  app.controller('AppController', [
    '$scope', 'Baseline', function($scope, Baseline) {
      return $scope.baselines = Baseline.query();
    }
  ]);

}).call(this);

(function() {
  var app;

  app = angular.module('baseline.api', ['ngResource']);

  app.factory('Baseline', [
    '$resource', function($resource) {
      return $resource('/api/baselines/:name', {
        name: '@name'
      });
    }
  ]);

}).call(this);
