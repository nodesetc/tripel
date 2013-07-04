var trplApp = angular.module('trpl', ['ngResource', 'ui.state']);

//TODO: should avoid also defining rootPath here, since it's already defined in python
trplApp.value('trplConstants', {rootPath: '/tripel'});

trplApp.config(
	function($stateProvider, $routeProvider) {
		$stateProvider
			.state('appView', { 
					url: '/app_view', 
					template: '<toptabs pane-list-type="app-views"></toptabs>',
					abstract: true
				}).
			state('appView.metaspaceCmds', {
					url: '/metaspace_cmds',
					templateUrl: 'static/ng_partials/metaspace_commands.html'
				}).
			state('appView.manageLoggedInUsr', {
					url: '/manage_logged_in_user',
					templateUrl: 'static/ng_partials/manage_logged_in_user.html'
				}).
			state('appView.nodespaceList', {
					url: '/nodespaces',
					templateUrl: 'static/ng_partials/nodespace_list.html'
				});
	}
);

trplApp.service('trplBackendSvc',
	function($http, trplConstants) {
		this.isAllowedToUse = function(pageName, callbackFn) {
			$http.get(trplConstants.rootPath+'/'+pageName, {params: {modeselektion: 'check_is_allowed_to_use'}}).
				success(function(data, status, headers, config) {
					var isAllowedToUse = false;
					if(data.is_allowed_to_use !== undefined) isAllowedToUse = (data.is_allowed_to_use === true);
					callbackFn(isAllowedToUse);
				}).
				error(function(data, status, headers, config) {
					callbackFn(false);
				});
		}
	}
);

//TODO: you're going to regret putting off localization...
trplApp.service('paneListSvc', 
	function(trplBackendSvc) {
		this.getPaneList = function(paneListType) {
			switch(paneListType) {
				//TODO: urlBase values should come from state info so we're not repeating the definition here
				case 'app-views':
					var urlBase = '#/app_view/';
					var panes = [{title: 'metaspace commands', url: urlBase+'metaspace_cmds', isSelected: false, isUsable: false},
							{title: 'manage logged in user', url: urlBase+'manage_logged_in_user', isSelected: false, isUsable: true},
							{title: 'accessible nodespaces', url: urlBase+'nodespaces', isSelected: true, isUsable: true}];
					
					var callbackFn = function(isAllowedToUseMetaspaceCmds) {
						panes[0].isUsable = isAllowedToUseMetaspaceCmds;
					}
					
					trplBackendSvc.isAllowedToUse('metaspace_command_list', callbackFn);
					
					return panes;
					
				case 'metaspace-commands':
					var urlBase = '#/app_view/metaspace_cmds/';
					var panes = [{title: 'create new nodespace', url: urlBase+'nodespace_create', isSelected: false, isUsable: false},
							{title: 'invite new user', url: urlBase+'user_invite_create', isSelected: false, isUsable: true},
							{title: 'list all nodespaces', url: urlBase+'nodespace_list', isSelected: false, isUsable: true},
							{title: 'list all users', url: urlBase+'user_list_all', isSelected: false, isUsable: true}];
					
					return panes
					
				default:
					return [];
			}
		};
	}
);

trplApp.controller('SelectPaneCtrl', 
	function($scope, $element, $state, paneListSvc) {
		$scope.paneListType = $element.attr('pane-list-type');
		
		var panes = $scope.panes = paneListSvc.getPaneList($scope.paneListType);
		
		$scope.select = function(pane) {
			angular.forEach(panes, function(curPane) {
				curPane.isSelected = false;
			});
			pane.isSelected = true;
		};
	}
);

trplApp.directive('toptabs', 
	function() {
		return {
			restrict: 'E',
			replace: true,
			scope: {},
			
			controller: 'SelectPaneCtrl',
			templateUrl: 'static/ng_partials/tab_top_container.html'
		};
	}
);

trplApp.directive('sidetabs', 
	function() {
		return {
			restrict: 'E',
			replace: true,
			scope: {},
			
			controller: 'SelectPaneCtrl',
			templateUrl: 'static/ng_partials/tab_side_container.html'
		};
	}
);
