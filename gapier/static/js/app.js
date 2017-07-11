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
    $routeProvider.when('/add_bundle_sheet', {
        templateUrl: '/static/partials/add_bundle_sheet.html',
        controller: AddBundleSheetCntl
    });
    $routeProvider.when('/create_bundle', {
        templateUrl: '/static/partials/create_bundle.html',
        controller: CreateBundleCntl
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

function ListCntl($scope, $routeParams, $route, $http, $location, $rootScope) {
    $scope.name = "ListCntl";
    $scope.params = $routeParams;
    $scope.opened = {};
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
    $scope.add_bundle_sheet = function(token) {
        $rootScope.sheet_data = { worksheet_token : token };
        $location.path('/add_bundle_sheet')
    }
    $scope.create_bundle = function(token) {
        $rootScope.bundle_data = { worksheet_token : token };
        $location.path('/create_bundle')
    }
    $scope.log = function(token) {
        var url = get_my_url( $scope ) + '/fetch?worksheet_token=' + token;
        console.log('Sending JSONP request to ' + url);
        $.ajax({
            url: url,
            callback: '?',
            dataType: 'jsonp',
            success: function(result){
                console.log(JSON.stringify(result,null,2));
                console.log(result);
            }
        });
    }
    $scope.remove_token = function( token ) {
        if ( ! confirm( 'Really remove ' + token + '?') ) {
            return;
        }
        $http.post( '/remove_token', { token : token } ).
            success( function() {
                $route.reload();
            } ).
            error( function() {
                alert("fail");
            } );
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
    var url = get_my_url( $scope );
    $scope.client_data = {
        "client_id" : gapier_variables.prefill_client_id,
        "client_secret" : gapier_variables.prefill_client_secret,
        "gapier_url" : url
    };
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
    $scope.cancel = create_reseting_cancel_to_list_handler( $scope, $rootScope, 'alias_data' );
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
    $scope.cancel = create_reseting_cancel_to_list_handler( $scope, $rootScope, 'alias_data' );
}

function AddCntl($scope, $routeParams, $http, $rootScope ) {
    $scope.name = "AddCntl";
    $scope.params = $routeParams;
    $scope.alias_data = { access_mode : 'full' };
    $scope.advanced = { show : 0 }

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
                delete $rootScope.alias_data;
                $scope.$location.path('/list');
            } ).
            error( function() {
                alert("fail");
            } )
    };

    $scope.cancel = create_reseting_cancel_to_list_handler( $scope, $rootScope, 'alias_data' );
}

function AddBundleSheetCntl($scope, $routeParams, $http, $rootScope ) {
    $scope.name = "AddBundleSheetCntl";
    $scope.params = $routeParams;
    $scope.sheet_data = { access_mode : 'full' };
    $scope.advanced = { show : 0 }

    var charmap = "abcdefghijklmnopqrstuvwxyz";
    var password = '';
    for ( var i = 0; i < 16; i++ ) {
        password += charmap.charAt( Math.floor( Math.random() * charmap.length) );
    }
    $scope.sheet_data.password = password;

    var from_alias = $rootScope.sheet_data.worksheet_token.split(/\:/)[0];

    $scope.$watch('sheet_data.title', function() {
        if ( $scope.sheet_data.title ) {
            var key = $scope.sheet_data.title.toLowerCase();
            key = key.replace(/[^a-z0-9\-]/g,'');
            $scope.sheet_data.key = key;
            $scope.sheet_data.alias = from_alias + '-' + key;
        }
        else {
            $scope.sheet_data.key = '';
            $scope.sheet_data.alias = '';
        }
    });

    $scope.add = function() {
        if ( ! $scope.sheet_data.title ) {
            return alert( 'Title needs to be specified.')
        }
        if ( ! $scope.sheet_data.columns ) {
            return alert( 'At least one column is needed')
        }
        if ( ! $scope.sheet_data.key ) {
            return alert( 'Key needs to be specified.')
        }
        if ( ! $scope.sheet_data.alias ) {
            return alert( 'Alias needs to be specified.')
        }

        $rootScope.sheet_data.title = $scope.sheet_data.title;
        $rootScope.sheet_data.columns = $scope.sheet_data.columns;
        $rootScope.sheet_data.key = $scope.sheet_data.key;
        $rootScope.sheet_data.alias = $scope.sheet_data.alias;
        $rootScope.sheet_data.access_mode = $scope.sheet_data.access_mode;
        $rootScope.sheet_data.password = $scope.sheet_data.password;

        $http.post( '/add_bundle_sheet', $rootScope.sheet_data ).
            success( function( result ) {
                delete $rootScope.sheet_data;
                $scope.$location.path('/list');
            } ).
            error( function() {
                alert("fail");
            } )
    };

    $scope.cancel = create_reseting_cancel_to_list_handler( $scope, $rootScope, 'sheet_data' );
}

function CreateBundleCntl($scope, $routeParams, $http, $rootScope ) {
    $scope.name = "CreateBundleCntl";
    $scope.params = $routeParams;
    $scope.bundle_data = { access_mode : 'read-only', title : 'Gapier Bundle' };
    $scope.advanced = { show : 0 }

    var charmap = "abcdefghijklmnopqrstuvwxyz";
    var password = '';
    for ( var i = 0; i < 16; i++ ) {
        password += charmap.charAt( Math.floor( Math.random() * charmap.length) );
    }
    $scope.bundle_data.password = password;

    $scope.add = function() {
        if ( ! $scope.bundle_data.alias ) {
            return alert( 'Alias needs to be specified.')
        }
        if ( ! $scope.bundle_data.title ) {
            return alert( 'Title needs to be specified.')
        }

        $rootScope.bundle_data.alias = $scope.bundle_data.alias;
        $rootScope.bundle_data.title = $scope.bundle_data.title;
        $rootScope.bundle_data.access_mode = $scope.bundle_data.access_mode;
        $rootScope.bundle_data.password = $scope.bundle_data.password;

        $http.post( '/create_bundle', $rootScope.bundle_data ).
            success( function( result ) {
                delete $rootScope.bundle_data;
                $scope.$location.path('/list');
            } ).
            error( function() {
                alert("fail");
            } )
    };

    $scope.cancel = create_reseting_cancel_to_list_handler( $scope, $rootScope, 'bundle_data' );
}

function create_reseting_cancel_to_list_handler( $scope, $rootScope, data_key ) {
    return function() {
        delete $rootScope[data_key];
        $scope.$location.path('/list');
    }
}

function get_my_url( $scope ) {
    var url = $scope.$location.protocol() + '://' + $scope.$location.host();
    var port = $scope.$location.port();
    if ( port && port != 80 && port != 443 ) {
        url = url + ':' + port;
    }
    return url;
}
