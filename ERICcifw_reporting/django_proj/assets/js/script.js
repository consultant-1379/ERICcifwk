var timeout;
$(document).ready(function () {
  $('body').addClass('loading');
  $('#buildLogError').hide();
  function waitForElement() {
    $('#dataContent').bind("DOMSubtreeModified",function(){
      clearTimeout(timeout);
      $('body').removeClass('loading');
      $('#dataContent').unbind();
    });
  }
  function pageTimeOutElement(id) {
    timeout = setTimeout(function () {
      if (document.getElementById(id)) {
        $('body').removeClass('loading');
      } else {
        $('body').removeClass('loading');
        $('#buildLogError').show();
      }
    }, 10000);
  }
  waitForElement();
  pageTimeOutElement("status");
});
(function() {
  var app;

  app = angular.module('baseline.app.basic', ['baseline.api', 'ngRoute']);

  app.config([
    '$routeProvider', '$locationProvider', '$interpolateProvider', function($routeProvider, $locationProvider, $interpolateProvider) {
      $locationProvider.html5Mode(true);
      $interpolateProvider.startSymbol('{[{');
      return $interpolateProvider.endSymbol('}]}');
    }
  ]);

  app.controller('AppController', [
    '$scope', '$route', '$location', '$routeParams', '$timeout', '$compile', '$interval', '$filter', 'DeploymentBaselineService', function($scope, $route, $location, $routeParams, $timeout, $compile, $interval, $filter, DeploymentBaselineService) {
      var daysOfWeek, isSelected, weeksOfYear;
      $scope.path = $location.path();
      $scope.dropPath = $scope.path.split("/");
      $scope.baselines = {};
      daysOfWeek = [];
      weeksOfYear = [];
      $scope.overAllSlot = [];
      $scope.baselineLength = 0;
      $scope.itemsPerPage = 9999;
      isSelected = function(element) {
        return element;
      };
      $scope.showOptions = false;
      $scope.toggle = function() {
        $scope.showOptions = !$scope.showOptions;
      };
      $scope.checkboxSelected = [];
      $scope.update = function() {
        $scope.count = $scope.checkboxSelected.filter(isSelected).length;
      };
      $scope.checkForUpdates = function() {
        $scope.deployments2 = DeploymentBaselineService.baselines.query({
          type: 'drop',
          dropName: $scope.drop
        });
        $scope.deployments2.$promise.then(function(deployments) {
          if ($scope.baselines.length === void 0 && deployments.length > 0) {
            return angular.forEach(deployments, function(deployment, key) {
              var deliveryGroup, deliveryGroupList, i, j, keys, ref;
              $scope.baselines[key] = deployment;
              deliveryGroup = JSON.stringify(deployment.deliveryGroup);
              if (deliveryGroup === 'null') {
                deployment.deliveryGroup = '';
              } else {
                deliveryGroupList = deployment.deliveryGroup.split(',');
                for (i = j = 0, ref = deliveryGroupList.length - 1; 0 <= ref ? j <= ref : j >= ref; i = 0 <= ref ? ++j : --j) {
                  if (deliveryGroupList[i].charAt(0) !== '-' && deliveryGroupList[i].charAt(1) !== '') {
                    deliveryGroupList[i] = '+' + deliveryGroupList[i];
                  }
                  deployment.deliveryGroup = deliveryGroupList;
                }
              }
              deployment.deliveryGroup.sort(function(software, testware) {
                return software.length - testware.length;
              });
              keys = Object.keys($scope.baselines);
              $scope.baselineLength = keys.length;
              weeksOfYear[keys.length - 1] = $filter('date')(new Date(deployment['createdAt']), 'ww');
              daysOfWeek[keys.length - 1] = new Date(deployment['createdAt']).getDay();
              return $scope.baselines[key].descriptionDetails = 'Wk ' + weeksOfYear[keys.length - 1] + '.' + daysOfWeek[keys.length - 1] + '.' + deployment['slot'];
            });
          }
        });
      };
      $scope.updateView = function() {
        if ($scope.dropPath.length === 4) {
          $scope.deployments = DeploymentBaselineService.baselines.query();
        } else if ($scope.dropPath.length === 5) {
          $scope.drop = $scope.dropPath[$scope.dropPath.length - 2];
          $scope.deployments = DeploymentBaselineService.baselines.query({
            type: 'drop',
            dropName: $scope.drop
          });
        } else if ($scope.dropPath.length === 6) {
          $scope.drop = $scope.dropPath[$scope.dropPath.length - 3];
          $scope.group = $scope.dropPath[$scope.dropPath.length - 2];
          if ($scope.group === "master") {
            $scope.deployments = DeploymentBaselineService.baselines.query({
              type: 'dropmaster',
              dropName: $scope.drop
            });
          } else {
            $scope.deployments = DeploymentBaselineService.baselines.query({
              type: 'dropgroup',
              dropName: $scope.drop,
              groupName: $scope.group
            });
          }
        }
        return $scope.checkForUpdates();
      };
      $scope.updateView();
      $scope.showflag = false;
      setTimeout((function() {
        $scope.$apply(function() {
          $scope.showflag = false;
          if ($scope.baselineLength === 0) {
            $scope.hideLoad();
            $scope.showflag = true;
          }
        });
      }), 1000);
      $scope.options = [
        {
          name: 'BUSY',
          value: '1'
        }, {
          name: 'IDLE',
          value: '2'
        }, {
          name: 'QUARANTINE',
          value: '3'
        }
      ];
      $scope.commentUser = 'None';
      $scope.userCommenting = false;
      $scope.appendUser = function(text) {
        $scope.commentUser = text;
      };
      $scope.loadingScreen = true;
      $scope.hideLoad = function() {
        return $timeout((function() {
          $scope.$apply(function() {
            $scope.loadingScreen = false;
          });
        }), 1000);
      };
      $scope.setMaster = function(id, drop) {
        $scope.updatedMaster = DeploymentBaselineService.updateMaster.save({
          'id': id,
          'drop': drop,
          'master': 'true'
        });
        return $scope.updatedMaster.$promise.then(function(result) {
          return $timeout(function() {
            return $scope.updateView();
          });
        });
      };
      $scope.updateTaf = function(id, version) {
        return $scope.updatedTaf = DeploymentBaselineService.updateTaf.save({
          'id': id,
          'taf': version
        });
      };

      var result;
      $scope.updateComment = function(id, index) {
        elId = "area" + id;
        var comment = document.getElementById(elId).value;

        if (comment !== '') {
          comment = comment + ' - ' + $scope.commentUser;
        }
        return $scope.updatedComment = DeploymentBaselineService.updateComment.save({
                'id': id,
                'comment': comment
        });
      };

      if (!String.prototype.startsWith) {
        String.prototype.startsWith = function(searchString, position) {
          position = position || 0;
          return this.indexOf(searchString, position) === position;
        };
      }
      if (!String.prototype.endsWith) {
        String.prototype.endsWith = function(pattern) {
          var d;
          d = this.length - pattern.length;
          return d >= 0 && this.lastIndexOf(pattern) === d;
        };
      }
      $scope.updateAvailability = function(id, availability) {
        availability = $scope.options[availability - 1];
        return $scope.updatedAvailability = DeploymentBaselineService.updateAvailability.save({
          'id': id,
          'availability': availability.name
        });
      };
      return $scope.cancelComment = function(id, comment, index) {
        $scope.baselines[$scope.baselineLength - index - 1].comment = comment;
        return $scope.checkForUpdates();
      };
    }
  ]);

  app.filter('orderByDrop', function() {
    return function(items) {
      var baselines;
      baselines = [];
      angular.forEach(items, function(item) {
        return baselines.push(item);
      });
      return baselines.sort(function(a, b) {
        var dropA, dropB, numberA, numberB;
        dropA = a.dropName.split('.');
        numberA = (parseInt(dropA[0]) * 100) + (parseInt(dropA[1]) * 10);
        dropB = b.dropName.split('.');
        numberB = (parseInt(dropB[0]) * 100) + (parseInt(dropB[1]) * 10);
        if (numberA > numberB) {
          return -1;
        }
        if (numberA < numberB) {
          return 1;
        }
        return 0;
      });
    };
  });

  app.filter('slice', function() {
    return function(arr, start, end) {
      return arr.slice(start, end);
    };
  });

}).call(this);

(function() {
  angular.module('app', ['ngRoute', 'ngAnimate', 'ngResource', 'app.components', 'ui.bootstrap', 'ngMessages']);

}).call(this);

(function() {
  angular.module('app.components', ['app.components.dmt']);

}).call(this);

(function() {
  angular.module('app.components.dmt', ['app.components.dmt.services', 'baseline.api', 'ui.bootstrap', 'ngMessages']);

}).call(this);

(function() {
  (function() {
    var EditModalCtrl, UtilizationController, config;
    UtilizationController = function(DeploymentBaselineService, ServerUtilizationService, $filter, $modal, OrderByPercentFilter) {
      var getBaselineInfo, init, latestResults, populateClusters, populateGroupMappings, populateGroups, populateTestcases;
      init = (function(_this) {
        return function() {
          var date;
          _this.testcaseDescriptions = {};
          _this.summaryResults = {};
          _this.overallResults = {};
          _this.clusters = [];
          _this.groups = [];
          _this.groupMappings = {};
          _this.curDate = null;
          _this.noData = false;
          _this.failureCounts = 0;
          _this.totalServers = 0;
          _this.defaultGroup = null;
          _this.showDivs = {
            'checks': false,
            'groups': false,
            'mappings': false,
            'filter': false
          };
          _this.showMsgs = {
            'checks': false,
            'groups': false,
            'mappings': false,
            'filter': false
          };
          _this.checkMsg = null;
          _this.groupMsg = null;
          _this.mapMsg = null;
          date = new Date();
          _this.curDate = $filter('date')(new Date(), 'dd-MM-yyyy');
          populateTestcases();
          populateGroups();
          populateGroupMappings();
          return populateClusters();
        };
      })(this);
      populateTestcases = (function(_this) {
        return function() {
          return ServerUtilizationService.testcases.query().$promise.then(function(data) {
            return angular.forEach(data, function(testcaseDesc) {
              return _this.testcaseDescriptions[testcaseDesc.id] = testcaseDesc;
            });
          });
        };
      })(this);
      populateGroups = (function(_this) {
        return function() {
          return ServerUtilizationService.groups.query().$promise.then(function(data) {
            angular.forEach(data, function(group) {
              if (group['defaultGroup'] === true) {
                _this.defaultGroup = group['testGroup'];
              }
              return _this.groups.push(group);
            });
            return latestResults();
          });
        };
      })(this);
      populateClusters = (function(_this) {
        return function() {
          return ServerUtilizationService.clusters.query().$promise.then(function(data) {
            return angular.forEach(data, function(cluster) {
              return _this.clusters.push(cluster);
            });
          });
        };
      })(this);
      populateGroupMappings = (function(_this) {
        return function() {
          return ServerUtilizationService.groupMappings.query().$promise.then(function(data) {
            return angular.forEach(data, function(groupMapping) {
              return _this.groupMappings[Object.keys(_this.groupMappings).length] = groupMapping;
            });
          });
        };
      })(this);
      latestResults = (function(_this) {
        return function() {
          return ServerUtilizationService.latestResults.query({
            date: _this.curDate,
            group: _this.defaultGroup
          }).$promise.then(function(data) {
            angular.forEach(data, function(testResults) {
              var id, keepGoing;
              keepGoing = true;
              if (_this.summaryResults[testResults.clusterName] === void 0) {
                id = testResults.clusterName.split(' ')[0];
                _this.summaryResults[testResults.clusterName] = [
                  {
                    "id": id,
                    "success": 0,
                    "total": 0,
                    "percent": 0,
                    "recentAutodeploy": false
                  }
                ];
              }
              angular.forEach(_this.summaryResults[testResults.clusterName], function(cluster) {
                if (testResults.testcase_description === cluster.testcase_description) {
                  return keepGoing = false;
                }
              });
              if (keepGoing) {
                _this.summaryResults[testResults.clusterName].push(testResults);
                _this.summaryResults[testResults.clusterName].jobRan = false;
                if (testResults.result === true) {
                  _this.summaryResults[testResults.clusterName][0].success += 1;
                }
                _this.summaryResults[testResults.clusterName][0].total += 1;
                return _this.summaryResults[testResults.clusterName][0].percent = (_this.summaryResults[testResults.clusterName][0].success / _this.summaryResults[testResults.clusterName][0].total) * 100;
              }
            });
            if (Object.keys(_this.summaryResults).length === 0) {
              _this.noData = true;
            }
            return getBaselineInfo();
          });
        };
      })(this);
      getBaselineInfo = (function(_this) {
        return function() {
          var totalUpdated;
          totalUpdated = false;
          return DeploymentBaselineService.baselines.query().$promise.then(function(data) {
            angular.forEach(data, function(testResults) {
              var date, result, testDate, weekAgoSeconds;
              if (testResults.clusterName in _this.summaryResults) {
                _this.summaryResults[testResults.clusterName].jobRan = true;
                testDate = new Date(testResults.createdAt);
                date = new Date();
                weekAgoSeconds = date.getTime() - (7 * 24 * 60 * 60 * 1000);
                date.setTime(weekAgoSeconds);
                result = false;
                if (testDate > date) {
                  result = true;
                  if (result === true) {
                    _this.summaryResults[testResults.clusterName][0].recentAutodeploy = true;
                  }
                }
                testDate = $filter('date')(new Date(testResults.createdAt), 'dd-MM-yyyy');
                return _this.summaryResults[testResults.clusterName].jobInfo = {
                  date: testDate,
                  details: testResults.descriptionDetails,
                  result: result
                };
              }
            });
            return angular.forEach(_this.summaryResults, function(value) {
              if (value[0].recentAutodeploy) {
                value[0].success += 1;
              }
              value[0].total += 1;
              return value[0].percent = (value[0].success / value[0].total) * 100;
            });
          });
        };
      })(this);
      this.addTestcase = (function(_this) {
        return function(desc, testcase, enabled) {
          var data;
          data = {
            'testcase_description': desc,
            'testcase': testcase,
            'enabled': enabled
          };
          return ServerUtilizationService.testcases.save(data).$promise.then((function(data) {
            _this.testcaseDescriptions[Object.keys(_this.testcaseDescriptions).length] = data;
            _this.showMsgs['checks'] = true;
            return _this.checkMsg = "Check added successfully";
          }), function() {
            _this.showMsgs['checks'] = true;
            return _this.checkMsg = "Error check inputs and login";
          });
        };
      })(this);
      this.addGroup = (function(_this) {
        return function(groupName) {
          var data;
          data = {
            'testGroup': groupName
          };
          return ServerUtilizationService.groups.save(data).$promise.then((function(data) {
            _this.groups[Object.keys(_this.groups).length] = data;
            _this.showMsgs['groups'] = true;
            return _this.groupMsg = "Group added successfully";
          }), function() {
            _this.showMsgs['groups'] = true;
            return _this.groupMsg = "Error check inputs and login";
          });
        };
      })(this);
      this.addMapping = (function(_this) {
        return function(groupMapName, clusterName) {
          var cluster, data, groupName;
          cluster = clusterName.name;
          groupName = groupMapName.testGroup;
          data = {
            'cluster': cluster,
            'group': groupName
          };
          return ServerUtilizationService.groupMappings.save(data).$promise.then((function(data) {
            _this.groupMappings[Object.keys(_this.groupMappings).length] = data;
            _this.showMsgs['mappings'] = true;
            return _this.mapMsg = "Mapping added successfully";
          }), function() {
            _this.showMsgs['mappings'] = true;
            return _this.mapMsg = "Error with request check login details";
          });
        };
      })(this);
      this.checkFilter = (function(_this) {
        return function(input) {
          return angular.forEach(_this.showDivs, function(key, value) {
            if (input === value) {
              if (_this.showDivs[value] === true) {
                _this.showDivs[value] = false;
                return _this.showMsgs[value] = false;
              } else {
                return _this.showDivs[value] = true;
              }
            } else {
              return _this.showDivs[value] = false;
            }
          });
        };
      })(this);
      this.updateFilterGroup = (function(_this) {
        return function(groupName) {
          _this.defaultGroup = groupName['testGroup'];
          _this.summaryResults = {};
          _this.noData = false;
          return latestResults();
        };
      })(this);
      this.editServerUtilisationCheck = function(id, description, checks, enabled) {
        var modalInstance;
        modalInstance = $modal.open({
          templateUrl: 'static/editServerUtilisationCheck.html',
          controller: 'EditModalCtrl as edit',
          windowClass: 'center-modal',
          resolve: {
            id: function() {
              return id;
            },
            description: function() {
              return description;
            },
            testcase: function() {
              return checks;
            },
            enabled: function() {
              return enabled;
            }
          }
        });
        return modalInstance.result.then((function(_this) {
          return function(data) {
            _this.testcaseDescriptions[data.id] = data;
          };
        })(this));
      };
      this.deleteServerUtilisationCheck = function(id, description, checks, enabled) {
        var modalInstance;
        modalInstance = $modal.open({
          templateUrl: 'static/deleteServerUtilisationCheck.html',
          controller: 'EditModalCtrl as edit',
          windowClass: 'center-modal',
          resolve: {
            id: function() {
              return id;
            },
            description: function() {
              return description;
            },
            testcase: function() {
              return checks;
            },
            enabled: function() {
              return enabled;
            }
          }
        });
        return modalInstance.result.then((function(_this) {
          return function(data) {
            delete _this.testcaseDescriptions[data.id];
          };
        })(this));
      };
      this.cancel = function() {};
      init();
    };
    EditModalCtrl = function(ServerUtilizationService, $modalInstance, id, description, testcase, enabled) {
      this.id = id;
      this.description = description;
      this.testcase = testcase;
      this.enabled = enabled;
      this.ok = (function(_this) {
        return function(id, desc, testcase, enabled) {
          var data;
          data = {
            'id': id,
            'testcase_description': desc,
            'testcase': testcase,
            'enabled': enabled
          };
          ServerUtilizationService.editServerUtilisationTestcases.save(data).$promise.then((function(data) {
            return $modalInstance.close(data);
          }));
        };
      })(this);
      this.okDelete = (function(_this) {
        return function(id) {
          var data;
          data = {
            'id': id
          };
          ServerUtilizationService.deleteServerUtilisationTestcases.save(data).$promise.then((function(data) {
            return $modalInstance.close(data);
          }));
        };
      })(this);
      this.cancel = function() {
        $modalInstance.dismiss('cancel');
      };
    };
    config = function($locationProvider, $interpolateProvider, $httpProvider) {
      $locationProvider.html5Mode(true);
      $interpolateProvider.startSymbol('{[{');
      $interpolateProvider.endSymbol('}]}');
      $httpProvider.defaults.headers.common['X-CSRFToken'] = $('input[name=csrfmiddlewaretoken]').val();
      return $httpProvider.defaults.headers.post['X-CSRFToken'] = $('input[name=csrfmiddlewaretoken]').val();
    };
    UtilizationController.$inject = ['DeploymentBaselineService', 'ServerUtilizationService', '$filter', '$modal'];
    return angular.module('app.components.dmt').controller('UtilizationController', UtilizationController).controller('EditModalCtrl', EditModalCtrl).config(config);
  })();

}).call(this);

(function() {
  (function() {
    var OrderByPercentFilter;
    OrderByPercentFilter = function() {
      return function(items) {
        var results;
        results = [];
        angular.forEach(items, function(item) {
          return results.push(item);
        });
        return results.sort(function(a, b) {
          var percentA, percentB;
          percentA = a[0].percent;
          percentB = b[0].percent;
          if (percentA > percentB) {
            return 1;
          }
          if (percentA < percentB) {
            return -1;
          }
          return 0;
        });
      };
    };
    return angular.module('app.components.dmt').filter('OrderByPercentFilter', OrderByPercentFilter);
  })();

}).call(this);

(function() {
  (function() {
    var ServerUtilizationService, config;
    ServerUtilizationService = function($resource) {
      return {
        clusters: $resource('/api/deployment/clusters/', {
          get: {
            method: 'GET',
            cache: true
          }
        }),
        groupMappings: $resource('/api/deployment/testgroup/mapping/'),
        groups: $resource('/api/deployment/testgroups/', {
          get: {
            method: 'GET',
            cache: true
          }
        }),
        latestResults: $resource('/api/deployment/testresults/date/:date/group/:group/', {
          date: '@date',
          group: '@group',
          get: {
            method: 'GET',
            cache: true
          }
        }),
        results: $resource('/api/deployment/testresults/', {
          get: {
            method: 'GET',
            cache: true
          }
        }),
        testcases: $resource('/api/deployment/testcases/', {
          get: {
            method: 'GET',
            cache: true
          }
        }),
        editServerUtilisationTestcases: $resource('/api/deployment/testcases/:id/edit-testcase/', {
          id: '@id'
        }),
        deleteServerUtilisationTestcases: $resource('/api/deployment/testcases/:id/delete-testcase/', {
          id: '@id'
        })
      };
    };
    ServerUtilizationService.$inject = ['$resource'];
    config = function($httpProvider, $resourceProvider) {
      $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
      $httpProvider.defaults.xsrfCookieName = 'csrftoken';
      return $resourceProvider.defaults.stripTrailingSlashes = false;
    };
    return angular.module('app.components.dmt.services', ['ngResource']).factory('ServerUtilizationService', ServerUtilizationService).config(config);
  })();

}).call(this);

(function() {
  (function() {
    var DeploymentBaselineService, config;
    DeploymentBaselineService = function($resource) {
      return {
        baselines: $resource('/api/deploymentbaseline/:type/:dropName/:groupName', {
          type: '@type',
          dropName: '@dropName',
          groupName: '@groupName',
          get: {
            method: 'GET',
            cache: true
          }
        }),
        getCommentVal: $resource('/api/deploymentbaseline/:id/', {
          id: '@id',
          get: {
            method: 'GET',
            cache: true,
          }
        }),
        updateMaster: $resource('/api/deploymentbaseline/:id/change-master/', {
          id: '@id'
        }),
        updateTaf: $resource('/api/deploymentbaseline/:id/change-taf/', {
          id: '@id'
        }),
        updateComment: $resource('/api/deploymentbaseline/:id/change-comment/', {
          id: '@id'
        }),
        updateAvailability: $resource('/api/deploymentbaseline/:id/change-availability/', {
          id: '@id'
        })
      };
    };
    DeploymentBaselineService.$inject = ['$resource'];
    config = function($httpProvider, $resourceProvider) {
      $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
      $httpProvider.defaults.xsrfCookieName = 'csrftoken';
      return $resourceProvider.defaults.stripTrailingSlashes = false;
    };
    return angular.module('baseline.api', ['ngResource']).factory('DeploymentBaselineService', DeploymentBaselineService).config(config);
  })();

}).call(this);
