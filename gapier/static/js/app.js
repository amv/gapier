angular.module('ngGapier', [], function($routeProvider, $locationProvider, $httpProvider ) {
    $routeProvider.when('/list', {
        templateUrl: '/static/partials/list.html',
        controller: ListCntl
    });
    $routeProvider.when('/authenticate', {
        templateUrl: '/static/partials/authenticate.html',
        controller: AuthenticateCntl
    });
    $routeProvider.when('/wrong_user', {
        templateUrl: '/static/partials/wrong_user.html',
        controller: WrongUserCntl
    });
    $routeProvider.when('/setup_client', {
        templateUrl: '/static/partials/setup_client.html',
        controller: SetupClientCntl
    });
    $routeProvider.when('/connect', {
        templateUrl: '/static/partials/connect.html',
        controller: ConnectCntl
    });
    $routeProvider.when('/add', {
        templateUrl: '/static/partials/add.html',
        controller: AddCntl
    });
    $routeProvider.when('/select', {
        templateUrl: '/static/partials/select.html',
        controller: SelectCntl
    });
});

function GapierCntl($scope, $route, $routeParams, $location, $http ) {
    $scope.$route = $route;
    $scope.$location = $location;
    $scope.$routeParams = $routeParams;

    if ( gapier_variables['wrong_user'] ) {
        $scope.$location.path('/wrong_user')
    }
    else if ( gapier_variables['login_url'] ) {
        $scope.$location.path('/authenticate')
    }
    else if ( ! gapier_variables['client_id'] ) {
        $scope.$location.path('/setup_client')
    }
    else if ( ! gapier_variables['credentials'] ) {
        $scope.$location.path('/connect')
    }
    else {
        $scope.$location.path('/list')
    }
}

function ListCntl($scope, $routeParams, $http, $location) {
    $scope.name = "ListCntl";
    $scope.params = $routeParams;
    $scope.urls = { logout_url : gapier_variables['logout_url'] }
    $http.get( '/list_tokens' ).success(function( data ){ $scope.aliases = data })
    $scope.add = function(){
        $location.path('/add')
    }
    $scope.curl = function(token){
        $(function () {
            var $temp = $("<input>");
            $("body").append($temp);
            $temp.val("curl '" + gapier_variables['client_url'] + "/fetch?worksheet_token="+token+"'").select();
            document.execCommand("copy");
            $temp.remove();
        });
    }
}

function AuthenticateCntl($scope, $routeParams) {
    $scope.name = "AuthenticateCntl";
    $scope.params = $routeParams;
    $scope.urls = { login_url : gapier_variables['login_url'] }
    $scope.expects = { expected_config_user_email : gapier_variables['expected_config_user_email'] }
}

function WrongUserCntl($scope, $routeParams) {
    $scope.name = "WrongUserCntl";
    $scope.params = $routeParams;
    $scope.urls = { logout_url : gapier_variables['logout_url'] }
    $scope.expects = { expected_config_user_email : gapier_variables['expected_config_user_email'] }
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
            success( function() { window.location = '/'; } ).
            error( function() { alert("fail"); } )
    };
}
function ConnectCntl($scope, $routeParams) {
    $scope.name = "ConnectCntl";
    $scope.params = $routeParams;
}
function AddCntl($scope, $routeParams, $rootScope ) {
    $scope.name = "AddCntl";
    $scope.params = $routeParams;
    $scope.alias_data = { access_mode : 'full' };

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
