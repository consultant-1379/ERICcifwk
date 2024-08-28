(->
  OrderByPercentFilter = ()->
      (items) ->
          results = []
          angular.forEach items, (item) ->
              results.push item

          results.sort (a,b) ->
              percentA = a[0].percent
              percentB = b[0].percent

              if percentA > percentB
                  return 1
              if percentA < percentB
                  return -1
              return 0

  angular
      .module('app.components.dmt')
      .filter('OrderByPercentFilter',OrderByPercentFilter)
)()
