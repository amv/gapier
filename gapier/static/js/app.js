angular.module('ngGapier', [], function($routeProvider, $locationProvider, $httpProvider ) {
    $routeProvider.when('/list', {
        templateUrl: '/static/partials/list.html',
        controller: ListCntl
    });
    $routeProvider.when('/authenticate', {
        templateUrl: '/static/partials/authenticate.html',
        controller: AuthenticateCntl
    });
    $routeProvider.when('/setup_client', {
        templateUrl: '/static/partials/setup_client.html',
        controller: SetupClientCntl
    });
    $routeProvider.when('/add', {
        templateUrl: '/static/partials/add.html',
        controller: AddCntl
    });
    $routeProvider.when('/select', {
        templateUrl: '/static/partials/select.html',
        controller: SelectCntl
    });
    $httpProvider.defaults.headers.common['Authorization'] = gapier_variables['config_secret'];
});

function GapierCntl($scope, $route, $routeParams, $location, $http ) {
    $scope.$route = $route;
    $scope.$location = $location;
    $scope.$routeParams = $routeParams;

    if ( ! gapier_variables['client_id'] ) {
        $scope.$location.path('/setup_client')
    }
    else if ( ! gapier_variables['config_secret'] ) {
        $scope.$location.path('/authenticate')
    }
    else {
        $scope.$location.path('/list')
    }
}

function ListCntl($scope, $routeParams, $http, $location) {
    $scope.name = "ListCntl";
    $scope.params = $routeParams;
    $http.get( '/list_tokens' ).success(function( data ){ $scope.aliases = data })
    $scope.add = function(){
        $location.path('/add')
    }
}

function AuthenticateCntl($scope, $routeParams) {
    $scope.name = "AuthenticateCntl";
    $scope.params = $routeParams;
}

function SetupClientCntl($scope, $routeParams, $http) {
    $scope.name = "SetupClientCntl";
    $scope.params = $routeParams;
    var url = $scope.$location.protocol() + '://' + $scope.$location.host();
    var port = $scope.$location.port();
    if ( port ) {
        url = url + ':' + port;
    }
    $scope.client_data = { "client_id" : "", "client_secret" : "", "gapier_url" : url };
    $scope.saveData = function() {
        $http.post( '/set_client', $scope.client_data ).
            success( function() { $scope.$location.path('/authenticate'); } ).
            error( function() { alert("fail"); } )
    };
}

function AddCntl($scope, $routeParams, $rootScope ) {
    $scope.name = "AddCntl";
    $scope.params = $routeParams;

    $scope.select = function() {
        $rootScope.alias_data = $scope.alias_data;

        var charmap = "abcdefghijklmnopqrstuvwxyz";
        var password = '';
        for ( var i = 0; i < 16; i++ ) {
            password += charmap.charAt( Math.floor( Math.random() * charmap.length) );
        }
        $rootScope.alias_data.password = password;

        $scope.$location.path('/select');
    };

    $scope.cancel = create_reseting_cancel_to_list_handler( $scope, $rootScope );
}

function SelectCntl($scope, $routeParams, $http, $rootScope ) {
    $scope.name = "SelectCntl";
    $scope.params = $routeParams;

    $http.get( '/get_document_sheet_list', { params : { spreadsheet_key : $rootScope.alias_data.spreadsheet_key } } ).
        success(function( data ){
            $scope.sheets = data;
            $scope.selected_title = data[0].title;
        } );

    $scope.create = function() {
        angular.forEach( $scope.sheets, function( sheet_data ) {
            if ( $scope.selected_title == sheet_data.title ) {
                $rootScope.alias_data.listfeed_url = sheet_data["src"];
            }
        } );

        $http.post( '/add_token', $rootScope.alias_data ).
            success( function() {
                reset_alias_data( $rootScope );
                $scope.$location.path('/list');
            } ).
            error( function() {
                alert("fail");
            } )
    };

    $scope.cancel = create_reseting_cancel_to_list_handler( $scope, $rootScope );
}

function reset_alias_data( $rootScope ) {
    delete $rootScope.alias_data;
}

function create_reseting_cancel_to_list_handler( $scope, $rootScope ) {
    return function() {
        reset_alias_data( $rootScope );
        $scope.$location.path('/list');
    }
}

