var trplApp = angular.module('trpl', ['ngResource', 'ui.state', 'jm.i18next']);

//TODO: should avoid also defining rootPath here, since it's already defined in python
var tripelRootPath = '/tripel'
var i18nOptions = {fallbackLng: 'en-US', resStore: window.trplLocaleMsgs, dynamicLoad: false}
i18n.init(i18nOptions);

trplApp.value('trplConstants', {rootPath: tripelRootPath});

trplApp.config(
	function($stateProvider, $routeProvider, $urlRouterProvider, $i18nextProvider) {
		$stateProvider
			.state('appView', { 
					url: '/app_view', 
					template: '<toptabs pane-list-type="app-views"></toptabs>',
					abstract: true
				})
			.state('appView.metaspaceCmds', {
					url: '/metaspace_cmds',
					templateUrl: 'static/ng_partials/metaspace_commands.html'
				})
			.state('appView.metaspaceCmds.nodespaceCreate', {
					url: '/nodespace_create',
					templateUrl: 'static/ng_partials/nodespace_edit.html'
				})
			.state('appView.metaspaceCmds.userInvitationCreate', {
					url: '/user_invitation_create',
					templateUrl: 'static/ng_partials/user_invitation_create.html'
				})
			.state('appView.metaspaceCmds.nodespaceListAll', {
					url: '/nodespaces_all',
					controller: 'NodespaceListAllCtrl',
					templateUrl: 'static/ng_partials/nodespace_list.html'
				})
			.state('appView.metaspaceCmds.nodespaceListAll.viewNodespace', {
					url: '/:nodespaceId',
					controller: 'NodespaceViewCtrl',
					templateUrl: 'static/ng_partials/nodespace_graph_view.html'
				})
			.state('appView.metaspaceCmds.userListAll', {
					url: '/users',
					templateUrl: 'static/ng_partials/user_list_metaspace.html'
				})
			.state('appView.manageLoggedInUser', {
					url: '/manage_logged_in_user',
					templateUrl: 'static/ng_partials/manage_logged_in_user.html'
				})
			.state('appView.manageLoggedInUser.editUserInfo', {
					url: '/user_info_edit',
					templateUrl: 'static/ng_partials/user_info_edit.html'
				})
			.state('appView.manageLoggedInUser.changeUserPassword', {
					url: '/user_change_password',
					templateUrl: 'static/ng_partials/user_change_password.html'
				})
			.state('appView.nodespaceListAccessible', {
					url: '/nodespaces_accessible',
					controller: 'NodespaceListAccessibleCtrl',
					templateUrl: 'static/ng_partials/nodespace_list.html'
				})
			.state('appView.nodespaceListAccessible.nodespaceInvitationCreate', {
					url: '/nodespace_invitation_create',
					templateUrl: 'static/ng_partials/nodespace_invitation_create.html'
				})
			.state('appView.nodespaceListAccessible.viewNodespace', {
					url: '/:nodespaceId',
					controller: 'NodespaceViewCtrl',
					templateUrl: 'static/ng_partials/nodespace_graph_view.html'
				});
		
		$urlRouterProvider.otherwise('/app_view/nodespaces_accessible');
	}
);

trplApp.service('trplBackendSvc',
	function($http, trplConstants) {
		this.isAllowedToUse = function(pageName, callbackFn) {
			$http.get(trplConstants.rootPath+'/'+pageName, {params: {modeselektion: 'check_is_allowed_to_use'}})
				.success(function(data, status, headers, config) {
					var isAllowedToUse = false;
					if(data.is_allowed_to_use !== undefined) isAllowedToUse = (data.is_allowed_to_use === true);
					callbackFn(isAllowedToUse);
				})
				.error(function(data, status, headers, config) {
					callbackFn(false);
				});
		};

		this.getObjList = function(callbackFn, subUri, params) {
			reqParams = jQuery.extend({}, params, {modeselektion: 'json'});
			reqUri = trplConstants.rootPath + subUri;
			$http.get(reqUri, {params: reqParams})
				.success(function(data, status, headers, config) {
					if((data.length !== undefined)) {
						callbackFn(data);
					} else {
						callbackFn([]);
					}
				})
				.error(function(data, status, headers, config) {
					callbackFn([]);
				});
		};

		this.getAccessibleNodespaces = function(callbackFn) {
			return this.getObjList(callbackFn, '/nodespace_list_accessible', {});
		};

		this.getAllNodespaces = function(callbackFn) {
			return this.getObjList(callbackFn, '/nodespace_list_all', {});
		};
		
		this.getGraphElements = function(callbackFn, nodespaceId) {
			return this.getObjList(callbackFn, '/nodespace_overview', {nodespace_id: nodespaceId});
		};
	}
);

trplApp.service('paneListSvc', 
	function(trplBackendSvc) {
		this.getPaneList = function(paneListType) {
			switch(paneListType) {
				//TODO: urlBase values should come from state info so we're not repeating the definition here
				case 'app-views':
					var urlBase = '#/app_view/';
					var panes = [{title: i18n.t('metaspace_command_list_smry'), url: urlBase+'metaspace_cmds', isSelected: false, isUsable: false},
							{title: i18n.t('manage_logged_in_user_tab_name'), url: urlBase+'manage_logged_in_user', isSelected: false, isUsable: true},
							{title: i18n.t('accessible_nodespaces_tab_name'), url: urlBase+'nodespaces_accessible', isSelected: false, isUsable: true}];
					
					var callbackFn = function(isAllowedToUseMetaspaceCmds) {
						panes[0].isUsable = isAllowedToUseMetaspaceCmds;
					}
					
					trplBackendSvc.isAllowedToUse('metaspace_command_list', callbackFn);
					
					return panes;
					
				case 'metaspace-commands':
					var urlBase = '#/app_view/metaspace_cmds/';
					var panes = [{title: i18n.t('nodespace_create_form_page_name'), url: urlBase+'nodespace_create', isSelected: false, isUsable: true},
							{title: i18n.t('user_invite_create_form_page_name'), url: urlBase+'user_invitation_create', isSelected: false, isUsable: true},
							{title: i18n.t('nodespace_list_all_page_name'), url: urlBase+'nodespaces_all', isSelected: false, isUsable: true},
							{title: i18n.t('user_list_all_page_name'), url: urlBase+'users', isSelected: false, isUsable: true}];
					
					return panes
				
				case 'manage-user':
					var urlBase = '#/app_view/manage_logged_in_user/';
					var panes = [{title: i18n.t('user_info_edit_form_page_name'), url: urlBase+'user_info_edit', isSelected: false, isUsable: true},
							{title: i18n.t('user_change_pass_form_page_name'), url: urlBase+'user_change_password', isSelected: false, isUsable: true}];
					
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

trplApp.controller('NodespaceListAllCtrl',
	function($scope, trplBackendSvc) {
		$scope.urlBase = '#/app_view/metaspace_cmds/nodespaces_all/';
		
		var nodespaceListData = $scope.nodespaceListData = {};
		var callbackFn = function(newNSList) {
			nodespaceListData.nodespaceList = newNSList;
		}
		trplBackendSvc.getAllNodespaces(callbackFn);
	}
);

trplApp.controller('NodespaceListAccessibleCtrl',
	function($scope, trplBackendSvc) {
		$scope.urlBase = '#/app_view/nodespaces_accessible/';
		
		var nodespaceListData = $scope.nodespaceListData = {};
		var callbackFn = function(newNSList) {
			nodespaceListData.nodespaceList = newNSList;
		}
		trplBackendSvc.getAccessibleNodespaces(callbackFn);
	}
);

trplApp.controller('NodespaceViewCtrl',
	function($scope, $stateParams, trplBackendSvc) {
		var nodespaceViewData = $scope.nodespaceViewData = {};
		var callbackFn = function(newGraphElements) {
			nodespaceViewData.graphElements = newGraphElements;
			var nsGraph = angular.element("#ns_graph").cytoscape("get");
			nsGraph.load(nodespaceViewData.graphElements);
		}
		trplBackendSvc.getGraphElements(callbackFn, $stateParams.nodespaceId);
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
