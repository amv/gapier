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
    $routeProvider.when('/add_choose_document', {
        templateUrl: '/static/partials/add_choose_document.html',
        controller: AddChooseDocumentCntl
    });
    $routeProvider.when('/add_select_sheet', {
        templateUrl: '/static/partials/add_select_sheet.html',
        controller: AddSelectSheetCntl
    });
    $routeProvider.when('/add', {
        templateUrl: '/static/partials/add.html',
        controller: AddCntl
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
        $location.path('/add_choose_document')
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
    $scope.clip = function(token){
        $(function () {
            var $temp = $("<input>");
            $("body").append($temp);
            $temp.val(token).select();
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

function AddChooseDocumentCntl($scope, $routeParams, $http, $rootScope ) {
    $scope.name = "AddChooseDocumentCntl";
    $scope.params = $routeParams;
    $rootScope.alias_data = {};

    $http.get( '/get_document_list' ).
        success(function( data ){
            $scope.documents = data.feed.entry;
        } ).
        error( function() {
            alert("failed fetching.. maybe reload and try again?");
        } );

    $scope.choose = function( key_or_url ) {
        if ( key_or_url ) {
            var keymatch = key_or_url.match(/([a-zA-Z0-9\-_]{20,80})/);
            if ( ! keymatch[1] ) {
                return alert( key_or_url + ' does not look like a proper key or a document url which would contain the key!')
            }
            $rootScope.alias_data.spreadsheet_key = keymatch[1];
            $scope.$location.path('/add_select_sheet');
        }
    }
    $scope.cancel = create_reseting_cancel_to_list_handler( $scope, $rootScope );
}

function AddSelectSheetCntl($scope, $routeParams, $http, $rootScope ) {
    $scope.name = "AddSelectSheetCntl";
    $scope.params = $routeParams;

    $http.get( '/get_document_sheet_list', { params : { spreadsheet_key : $rootScope.alias_data.spreadsheet_key } } ).
        success(function( data ){
            $scope.sheets = data;
            $scope.selected_title = data[0].title;
        } ).
        error( function() {
            alert("failed fetching.. maybe reload and try again?");
        } );

    $scope.select = function() {
        angular.forEach( $scope.sheets, function( sheet_data ) {
            if ( $scope.selected_title == sheet_data.title ) {
                $rootScope.alias_data.listfeed_url = sheet_data["src"];
            }
        } );
        $scope.$location.path('/add');
    };
    $scope.cancel = create_reseting_cancel_to_list_handler( $scope, $rootScope );
}

function AddCntl($scope, $routeParams, $http, $rootScope ) {
    $scope.name = "AddCntl";
    $scope.params = $routeParams;
    $scope.alias_data = { access_mode : 'full' };

    var charmap = "abcdefghijklmnopqrstuvwxyz";
    var password = '';
    for ( var i = 0; i < 16; i++ ) {
        password += charmap.charAt( Math.floor( Math.random() * charmap.length) );
    }
    $scope.alias_data.password = password;

    $scope.add = function() {
        if ( ! $scope.alias_data.alias ) {
            return alert( 'Alias needs to be specified.')
        }

        $rootScope.alias_data.alias = $scope.alias_data.alias;
        $rootScope.alias_data.access_mode = $scope.alias_data.access_mode;
        $rootScope.alias_data.password = $scope.alias_data.password;

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
