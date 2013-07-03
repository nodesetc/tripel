var trplApp = angular.module('trpl', ['ngResource', 'ui.state']);

//TODO: should avoid also defining rootPath here, since it's already defined in python
trplApp.value('trplConstants', {rootPath: '/tripel'});

trplApp.config(
	function($stateProvider, $routeProvider) {
		$stateProvider
			.state('appView', { 
					url: '/app_view', 
					template: '<tabs pane-list-type="app-views"></tabs>',
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
				case 'app-views':
					var panes = [{title: 'metaspace commands', url: '#/app_view/metaspace_cmds', isSelected: false, isUsable: false},
							{title: 'manage logged in user', url: '#/app_view/manage_logged_in_user', isSelected: false, isUsable: true},
							{title: 'accessible nodespaces', url: '#/app_view/nodespaces', isSelected: true, isUsable: true}];
					
					var callbackFn = function(isAllowedToUseMetaspaceCmds) {
						panes[0].isUsable = isAllowedToUseMetaspaceCmds;
					}
					
					trplBackendSvc.isAllowedToUse('metaspace_command_list', callbackFn);
					
					return panes;
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

trplApp.directive('tabs', 
	function() {
		return {
			restrict: 'E',
			replace: true,
			scope: {},
			
			controller: 'SelectPaneCtrl',
			templateUrl: 'static/ng_partials/tab_container.html'
		};
	}
);

