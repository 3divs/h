get_quote = (annotation) ->
  if not 'target' in annotation then return ''
  quote = ''
  for target in annotation['target']
    for selector in target['selector']
        if selector['type'] is 'TextQuoteSelector' 
            quote = quote + selector['exact'] + ' '

  quote

  
angular.module('h.streamer',['h.filters'])
  .controller('StreamerCtrl',
  ($scope, $element) ->
    $scope.streaming = false
    $scope.annotations = []    

    $scope.start_streaming = ->
      sock = new SockJS(window.location.protocol + '//' + window.location.hostname + ':' + port + '/streamer')    
      sock.onopen = ->
        $scope.$apply =>
          $scope.streaming = true
      sock.onclose = ->
        $scope.$apply =>
          $scope.streaming = false
      sock.onmessage = (msg) =>
        $scope.$apply =>
          console.log msg.data
          msg.data['quote'] = get_quote msg.data
          $scope.annotations.push msg.data
  )


