var trplApp = angular.module('trpl', ['ngResource', 'ui.state', 'jm.i18next']);


i18n.init({fallbackLng: 'en-US', 
			resStore: window.trplLocaleMsgs, 
			dynamicLoad: false});


//TODO: should avoid also defining rootPath here, since it's already defined in python
trplApp.value('trplConstants', {rootPath: '/tripel',
								dateFormat: 'yyyy-MM-dd HH:mm:ss Z'});

trplApp.value('trplEvents', {selectNodespace: 'selectNodespace',
								selectUser: 'selectUser'});


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
					controller: 'CreateNodespaceCtrl',
					templateUrl: 'static/ng_partials/nodespace_edit.html'
				})
			.state('appView.metaspaceCmds.userInvitationCreate', {
					url: '/user_invitation_create',
					controller: 'CreateUserInvitationCtrl',
					templateUrl: 'static/ng_partials/user_invitation_create.html'
				})
			.state('appView.metaspaceCmds.nodespaceListAll', {
					url: '/nodespaces_all',
					controller: 'NodespaceListAllCtrl',
					templateUrl: 'static/ng_partials/nodespace_list.html'
				})
			.state('appView.metaspaceCmds.nodespaceListAll.selectNodespace', {
					url: '/:nodespaceId',
					controller: 'SelectNodespaceCtrl',
					templateUrl: 'static/ng_partials/nodespace_view_msadmin.html'
				})
			.state('appView.metaspaceCmds.nodespaceListAll.selectNodespace.nodespaceInfoEdit', {
					url: '/nodespace_info_edit',
					controller: 'EditNodespaceCtrl',
					templateUrl: 'static/ng_partials/nodespace_edit.html'
				})
			.state('appView.metaspaceCmds.nodespaceListAll.selectNodespace.userList', {
					url: '/user_list_nodespace',
					controller: 'UserListNodespaceAdminCtrl',
					templateUrl: 'static/ng_partials/user_list_nodespace.html'
				})
			.state('appView.metaspaceCmds.nodespaceListAll.selectNodespace.nodespaceGrantAccess', {
					url: '/nodespace_grant_access',
					controller: '',
					templateUrl: 'static/ng_partials/nodespace_grant_access.html'
				})
			.state('appView.metaspaceCmds.userListAll', {
					url: '/users',
					controller: 'UserListAllCtrl',
					templateUrl: 'static/ng_partials/user_list_metaspace.html'
				})
			.state('appView.metaspaceCmds.userListAll.selectUser', {
					url: '/:userId',
					controller: 'SelectUserCtrl',
					templateUrl: 'static/ng_partials/user_view_msadmin.html'
				})
			.state('appView.manageLoggedInUser', {
					url: '/manage_logged_in_user',
					templateUrl: 'static/ng_partials/manage_logged_in_user.html'
				})
			.state('appView.manageLoggedInUser.editUserInfo', {
					url: '/user_info_edit',
					controller: 'EditUserInfoCtrl',
					templateUrl: 'static/ng_partials/user_info_edit.html'
				})
			.state('appView.manageLoggedInUser.changeUserPassword', {
					url: '/user_change_password',
					controller: 'ChangePasswordCtrl',
					templateUrl: 'static/ng_partials/user_change_password.html'
				})
			.state('appView.nodespaceListAccessible', {
					url: '/nodespaces_accessible',
					controller: 'NodespaceListAccessibleCtrl',
					templateUrl: 'static/ng_partials/nodespace_list.html'
				})
			.state('appView.nodespaceListAccessible.selectNodespace', {
					url: '/:nodespaceId',
					controller: 'SelectNodespaceCtrl',
					templateUrl: 'static/ng_partials/nodespace_view.html'
				})
			.state('appView.nodespaceListAccessible.selectNodespace.browseNodes', {
					url: '/browse_nodes',
					controller: 'NodespaceBrowseCtrl',
					templateUrl: 'static/ng_partials/nodespace_browse_nodes.html'
				})
			.state('appView.nodespaceListAccessible.selectNodespace.nodespaceInfoEdit', {
					url: '/nodespace_info_edit',
					controller: 'EditNodespaceCtrl',
					templateUrl: 'static/ng_partials/nodespace_edit.html'
				})
			.state('appView.nodespaceListAccessible.selectNodespace.userList', {
					/*warning:  supposedly we shouldn't be able to get $stateParams.nodespaceId in this state, since 
					 that param is in the parent state.  but that param seems accessible from this state.
					 see:  https://github.com/angular-ui/ui-router/wiki/URL-Routing#wiki-important-stateparams-gotcha
					*/
					url: '/user_list_nodespace',
					controller: 'UserListNodespaceCtrl',
					templateUrl: 'static/ng_partials/user_list_nodespace.html'
				})
			.state('appView.nodespaceListAccessible.selectNodespace.userList.selectUser', {
					url: '/:userId',
					controller: 'SelectUserCtrl',
					templateUrl: 'static/ng_partials/user_view_nodespace.html'
				})
			.state('appView.nodespaceListAccessible.selectNodespace.nodespaceInvitationCreate', {
					url: '/nodespace_invitation_create',
					controller: 'CreateNodespaceInvitationCtrl',
					templateUrl: 'static/ng_partials/nodespace_invitation_create.html'
				});
		
		$urlRouterProvider.otherwise('/app_view/nodespaces_accessible');
	}
);

trplApp.service('trplBackendSvc',
	function($http, trplConstants) {
		this.isAllowedToUse = function(pageName, callbackFn) {
			var reqParams = {modeselektion: 'check_is_allowed_to_use'};
			var reqUri = trplConstants.rootPath+'/'+pageName;
			$http.get(reqUri, {params: reqParams})
				.success(function(data, status, headers, config) {
					var isAllowedToUse = false;
					if(data.is_allowed_to_use !== undefined) isAllowedToUse = (data.is_allowed_to_use === true);
					callbackFn(isAllowedToUse);
				})
				.error(function(data, status, headers, config) {
					callbackFn(false);
				});
		};
		
		this.httpReq = function(reqMethod, subUrl, params, successCallbackFn, errorCallbackFn) {
			var reqParams = jQuery.extend({}, params, {modeselektion: 'json'});
			var reqUrl = trplConstants.rootPath + subUrl;
			
			var reqConfig = {method: reqMethod, url: reqUrl};
			if(reqMethod == 'POST') {
			//by default, angular sends data over as json, we want the more traditional form encoding.
			//see also:  http://stackoverflow.com/questions/11442632/how-can-i-make-angular-js-post-data-as-form-data-instead-of-a-request-payload
			//           http://victorblog.com/2012/12/20/make-angularjs-http-service-behave-like-jquery-ajax/
				reqConfig['data'] = $.param(reqParams, true);
				reqConfig['headers'] = {'Content-Type': 'application/x-www-form-urlencoded'};
			} else {
				reqConfig['params'] = reqParams;
			}
			
			$http(reqConfig)
				.success(successCallbackFn)
				.error(errorCallbackFn);
		}
		
		this.reqObjList = function(reqMethod, callbackFn, subUrl, params) {
			var successCallbackFn = function(respData, status, headers, config) {
				if((respData.length !== undefined)) {
					callbackFn(respData);
				} else {
					callbackFn([]);
				}
			};
			
			var errorCallbackFn = function(respData, status, headers, config) {
				callbackFn(null);
			};
			
			this.httpReq(reqMethod, subUrl, params, successCallbackFn, errorCallbackFn);
		};
		
		this.reqObj = function(reqMethod, callbackFn, subUrl, params) {
			var successCallbackFn = function(respData, status, headers, config) {
				callbackFn(respData);
			};
			
			var errorCallbackFn = function(respData, status, headers, config) {
				callbackFn(null);
			};
			
			this.httpReq(reqMethod, subUrl, params, successCallbackFn, errorCallbackFn);
		}
		
		this.getObjList = function(callbackFn, subUrl, params) {
			this.reqObjList('GET', callbackFn, subUrl, params);
		};
		
		this.getObj = function(callbackFn, subUrl, params) {
			this.reqObj('GET', callbackFn, subUrl, params);
		};
		
		this.postReq = function(callbackFn, subUrl, params) {
			this.reqObj('POST', callbackFn, subUrl, params);
		}
		
		this.getAccessibleNodespaces = function(callbackFn) {
			return this.getObjList(callbackFn, '/nodespace_list_accessible', {});
		};

		this.getAllNodespaces = function(callbackFn) {
			return this.getObjList(callbackFn, '/nodespace_list_all', {});
		};
		
		this.getGraphElements = function(callbackFn, nodespaceId) {
			return this.getObjList(callbackFn, '/nodespace_overview', {nodespace_id: nodespaceId});
		};
		
		this.getAllUsers = function(callbackFn) {
			return this.getObjList(callbackFn, '/user_list_all', {});
		};
		
		this.getNodespaceUsers = function(callbackFn, nodespaceId) {
			return this.getObjList(callbackFn, '/user_list_nodespace', {nodespace_id: nodespaceId});
		};
		
		this.getNodespaceViewInfo = function(callbackFn, nodespaceId) {
			return this.getObj(callbackFn, '/nodespace_view', {nodespace_id: nodespaceId});
		};
		
		this.getAuthStatus = function(callbackFn) {
			return this.getObj(callbackFn, '/auth_status', {});
		};
		
		this.getUserViewInfo = function(callbackFn, viewedUserId) {
			return this.getObj(callbackFn, '/user_view', {viewed_user_id: viewedUserId});
		};
		
		this.updateUserInfo = function(callbackFn, userUpdData) {
			return this.postReq(callbackFn, '/user_info_edit', userUpdData);
		};
		
		this.updateUserPassword = function(callbackFn, pwUpdData) {
			return this.postReq(callbackFn, '/user_change_pass', pwUpdData);
		};
		
		this.createNodespace = function(callbackFn, nodespaceData) {
			return this.postReq(callbackFn, '/nodespace_create', nodespaceData);
		};
		
		this.editNodespace = function(callbackFn, nodespaceData) {
			return this.postReq(callbackFn, '/nodespace_edit', nodespaceData);
		};
		
		this.getGrantableMetaspacePrivileges = function(callbackFn) {
			return this.getObj(callbackFn, '/user_invitation_create_form', {});
		};
		
		this.createUserInvitation = function(callbackFn, invitationData) {
			return this.postReq(callbackFn, '/user_invitation_create', invitationData);
		};
		
		this.getGrantableNodespacePrivileges = function(callbackFn, nodespaceId) {
			return this.getObj(callbackFn, '/nodespace_invitation_create_form', {nodespace_id: nodespaceId});
		};
		
		this.createNodespaceInvitation = function(callbackFn, invitationData) {
			return this.postReq(callbackFn, '/nodespace_invitation_create', invitationData);
		};
	}
);

trplApp.service('paneListSvc', 
	function(trplBackendSvc, $stateParams) {
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
					};
					
					trplBackendSvc.isAllowedToUse('metaspace_command_list', callbackFn);
					
					return panes;
					
				case 'metaspace-commands':
					var urlBase = '#/app_view/metaspace_cmds/';
					var panes = [{title: i18n.t('nodespace_create_form_page_name'), url: urlBase+'nodespace_create', isSelected: false, isUsable: false},
							{title: i18n.t('user_invitation_create_form_page_name'), url: urlBase+'user_invitation_create', isSelected: false, isUsable: false},
							{title: i18n.t('nodespace_list_all_page_name'), url: urlBase+'nodespaces_all', isSelected: false, isUsable: false},
							{title: i18n.t('user_list_all_page_name'), url: urlBase+'users', isSelected: false, isUsable: false}];
					
					var callbackFn = function(isAllowedToUseCmd, pane) {
						pane.isUsable = isAllowedToUseCmd;
					};
					
					['nodespace_create', 'user_invitation_create', 'nodespace_list_all', 'user_list_all'].forEach(function(cmdName, idx, arr) {
							var paneCallbackFn = function(isAllowedToUseCmd) { callbackFn(isAllowedToUseCmd, panes[idx]); };
							trplBackendSvc.isAllowedToUse(cmdName, paneCallbackFn);
						}
					);
					
					return panes
				
				case 'manage-user':
					var urlBase = '#/app_view/manage_logged_in_user/';
					var panes = [{title: i18n.t('user_info_edit_form_page_name'), url: urlBase+'user_info_edit', isSelected: false, isUsable: true},
							{title: i18n.t('user_change_pass_form_page_name'), url: urlBase+'user_change_password', isSelected: false, isUsable: true}];
					
					return panes;
				
				case 'nodespace-view':
					var urlBase = '#/app_view/nodespaces_accessible/' + $stateParams.nodespaceId + '/';
					var panes = [{title: i18n.t('nodespace_browse_tab_label'), url: urlBase+'browse_nodes', isSelected: false, isUsable: true},
								{title: i18n.t('nodespace_edit_form_page_name'), url: urlBase+'nodespace_info_edit', isSelected: false, isUsable: false},
								{title: i18n.t('nodespace_user_list_tab_label'), url: urlBase+'user_list_nodespace', isSelected: false, isUsable: false},
								{title: i18n.t('nodespace_invitation_create_form_page_name'), url: urlBase+'nodespace_invitation_create', isSelected: false, isUsable: false}];
					
					var callbackFn = function(nodespaceViewResult) {
						var nodespaceViewCmdPerms = nodespaceViewResult.perms_for_user;
						panes[1].isUsable = nodespaceViewCmdPerms['is_allowed_to_edit_nodespace'];
						panes[2].isUsable = nodespaceViewCmdPerms['is_allowed_to_list_nodespace_users'];
						panes[3].isUsable = nodespaceViewCmdPerms['is_allowed_to_invite_nodespace_users'];
					}
					
					trplBackendSvc.getNodespaceViewInfo(callbackFn, $stateParams.nodespaceId);
					
					return panes;
				
				case 'nodespace-view-admin':
					var urlBase = '#/app_view/metaspace_cmds/nodespaces_all/' + $stateParams.nodespaceId + '/';
					var panes = [{title: i18n.t('nodespace_edit_form_page_name'), url: urlBase+'nodespace_info_edit', isSelected: false, isUsable: false},
								{title: i18n.t('nodespace_user_list_tab_label'), url: urlBase+'user_list_nodespace', isSelected: false, isUsable: false},
								{title: i18n.t('nodespace_grant_access_tab_label'), url: urlBase+'nodespace_grant_access', isSelected: false, isUsable: false}];
					
					var callbackFn = function(nodespaceViewResult) {
						var nodespaceViewCmdPerms = nodespaceViewResult.perms_for_user;
						panes[0].isUsable = nodespaceViewCmdPerms['is_allowed_to_edit_nodespace'];
						panes[1].isUsable = nodespaceViewCmdPerms['is_allowed_to_list_nodespace_users'];
						panes[2].isUsable = nodespaceViewCmdPerms['is_allowed_to_invite_nodespace_users'];
					}
					
					trplBackendSvc.getNodespaceViewInfo(callbackFn, $stateParams.nodespaceId);
					
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

var getTableListCallbackFn = function(tableListDataObj) {
	return function(objList) {
		tableListDataObj.rowList = objList;
	};
};

var getSelectRowFn = function(tableListDataObj) {
	return function(eventObj, selectedRowId) {
		tableListDataObj.selectedRowId = selectedRowId;
	};
};

var getUnselectRowFn = function(tableListDataObj) {
	return function() {
		tableListDataObj.selectedRowId = null;
	}
};

var getNodespaceListCtrlFn = function(urlBase, nodespaceListFnName) {
	//note that the function returned here assumes it'll get its params injected by angular upon invocation.  it's intended to be used to build controllers.
	return function($scope, trplBackendSvc, trplEvents) {
		$scope.urlBase = urlBase;
		
		var nodespaceListData = $scope.nodespaceListData = {selectedRowId: null, rowList: null};
		var callbackFn = getTableListCallbackFn(nodespaceListData);
		trplBackendSvc[nodespaceListFnName](callbackFn);
		
		var selectNodespaceFn = getSelectRowFn(nodespaceListData);
		$scope.$on(trplEvents.selectNodespace, selectNodespaceFn);
		
		var unselectNodespaceFn = getUnselectRowFn(nodespaceListData);
		$scope.unselectNodespace = unselectNodespaceFn;
	};
};

trplApp.controller('NodespaceListAllCtrl', getNodespaceListCtrlFn('#/app_view/metaspace_cmds/nodespaces_all', 'getAllNodespaces'));
trplApp.controller('NodespaceListAccessibleCtrl', getNodespaceListCtrlFn('#/app_view/nodespaces_accessible', 'getAccessibleNodespaces'));

trplApp.controller('SelectNodespaceCtrl',
	function($scope, $stateParams, trplEvents) {
		$scope.$emit(trplEvents.selectNodespace, $stateParams.nodespaceId);
	}
);

var userListAllCtrlName = 'UserListAllCtrl';
var userListNodespaceCtrlName = 'UserListNodespaceCtrl';
var userListNodespaceAdminCtrlName = 'UserListNodespaceAdminCtrl';

function getUserListCtrlFn(controllerName) {
	return function($scope, $stateParams, $filter, trplBackendSvc, trplConstants, trplEvents) {
		switch(controllerName) {
			case userListAllCtrlName:
				$scope.urlBase = '#/app_view/metaspace_cmds/users';
				break;
			case userListNodespaceCtrlName:
				$scope.urlBase = '#/app_view/nodespaces_accessible/'+$stateParams.nodespaceId+'/user_list_nodespace';
				break;
			case userListNodespaceAdminCtrlName:
				$scope.urlBase = '#/app_view/metaspace_cmds/nodespaces_all/'+$stateParams.nodespaceId+'/user_list_nodespace';
				break;
			default:
				$scope.urlBase = '#/';
		}
		
		$scope.dateFormat = trplConstants.dateFormat;
		
		var userListData = $scope.userListData = {selectedRowId: null, rowList: null};
		var callbackFn = function(userList) {
			userListData.rowList = userList;
			
			userListData.rowList.forEach(function(val, idx, arr) {
								if(val.creation_date != null) {
									val.creation_date = new Date(val.creation_date.replace(" ", "T"));
									val.creation_date = $filter('date')(val.creation_date, trplConstants.dateFormat);
								}
								
								if(val.modification_date != null) {
									val.modification_date = new Date(val.modification_date.replace(" ", "T"));
									val.modification_date = $filter('date')(val.modification_date, trplConstants.dateFormat);
								}
							});
							
		};
		switch (controllerName) {
			case userListAllCtrlName:
				trplBackendSvc.getAllUsers(callbackFn);
				break;
			case userListNodespaceCtrlName:
			case userListNodespaceAdminCtrlName:
				trplBackendSvc.getNodespaceUsers(callbackFn, $stateParams.nodespaceId);
				break;
		}
		
		var selectUserFn = getSelectRowFn(userListData);
		$scope.$on(trplEvents.selectUser, selectUserFn);
		
		var unselectUserFn = getUnselectRowFn(userListData);
		$scope.unselectUser = unselectUserFn;
	};
}

trplApp.controller('UserListAllCtrl', getUserListCtrlFn('UserListAllCtrl'));
trplApp.controller('UserListNodespaceCtrl', getUserListCtrlFn('UserListNodespaceCtrl'));
trplApp.controller('UserListNodespaceAdminCtrl', getUserListCtrlFn('UserListNodespaceAdminCtrl'));

trplApp.controller('SelectUserCtrl',
	function($scope, $stateParams, trplEvents) {
		$scope.$emit(trplEvents.selectUser, $stateParams.userId);
	}
);

trplApp.controller('NodespaceBrowseCtrl',
	function($scope, $stateParams, trplBackendSvc) {
		var nodespaceViewData = $scope.nodespaceViewData = {};
		var callbackFn = function(newGraphElements) {
			nodespaceViewData.graphElements = newGraphElements;
			var nsGraph = angular.element("#ns_graph").cytoscape("get");
			nsGraph.load(nodespaceViewData.graphElements);
		};
		trplBackendSvc.getGraphElements(callbackFn, $stateParams.nodespaceId);
	}
);

trplApp.controller('EditUserInfoCtrl',
	function($scope, trplBackendSvc) {
		var userInfo = $scope.userInfo = {};
		var updateStatus = $scope.updateStatus = {'encounteredUpdateError': null};
		
		var userInfoCallbackFn = function(userInfoResult) {
			userInfo = $scope.userInfo = userInfoResult;
		};
		
		var authStatusCallbackFn = function(authInfo) {
			trplBackendSvc.getUserViewInfo(userInfoCallbackFn, authInfo.user_id);
		};
		
		var userUpdateCallbackFn = function(updResult) {
			if (updResult == null) {
				updateStatus.encounteredUpdateError = true;
			} else {			
				updateStatus.encounteredUpdateError = Boolean(updResult.encountered_update_error);
			}
		};
		
		var submitEditForm = function() {
			var userUpdData = {'edited_user_id': userInfo.user_id,
								'username': userInfo.username,
								'email_addr': userInfo.email_addr,
								'user_statement': userInfo.user_statement};
			trplBackendSvc.updateUserInfo(userUpdateCallbackFn, userUpdData);
		};
		$scope.submitEditForm = submitEditForm;
		
		//the fn call to get the user info will be invoke by this call to get the auth info
		trplBackendSvc.getAuthStatus(authStatusCallbackFn);
	}
);

trplApp.controller('ChangePasswordCtrl',
	function($scope, trplBackendSvc) {
		var pwInfo = $scope.pwInfo = {};
		var updateStatus = $scope.updateStatus = {'encounteredUpdateError': null};
		
		var authStatusCallbackFn = function(authInfo) {
			pwInfo.edited_user_id = authInfo.user_id;
		};
		trplBackendSvc.getAuthStatus(authStatusCallbackFn);
		
		var passwordUpdateCallbackFn = function(updResult) {
			if (updResult == null) {
				updateStatus.encounteredUpdateError = true;
			} else {			
				updateStatus.encounteredUpdateError = Boolean(updResult.encountered_update_error);
				updateStatus.errorMsg = updResult.error_msg;
			}
		};
		
		var submitPasswordChangeForm = function() {
			var pwUpdData = {'edited_user_id': pwInfo.edited_user_id,
								'editing_user_cleartext_password': pwInfo.editing_user_cleartext_password,
								'cleartext_password_1': pwInfo.cleartext_password_1,
								'cleartext_password_2': pwInfo.cleartext_password_2};
			trplBackendSvc.updateUserPassword(passwordUpdateCallbackFn, pwUpdData);
		};
		$scope.submitPasswordChangeForm = submitPasswordChangeForm;
	}
);

trplApp.controller('CreateNodespaceCtrl',
	function($scope, trplBackendSvc) {
		var nodespaceInfo = $scope.nodespaceInfo = {};
		var updateStatus = $scope.updateStatus = {'encounteredUpdateError': null};
		var createStatus = $scope.createStatus = {'encounteredCreateError': null};
		$scope.submitBtnContentKey = 'create_ns_submit_btn';
		
		var nodespaceCreateCallbackFn = function(createResult) {
			if (createResult == null) {
				createStatus.encounteredCreateError = true;
			} else {
				createStatus.encounteredCreateError = Boolean(createResult.encountered_create_error);
			}
		};
		
		var submitNodespaceCreateForm = function() {
			var nsCreateData = {'nodespace_name': nodespaceInfo.nodespace_name, 'nodespace_description': nodespaceInfo.nodespace_description};
			trplBackendSvc.createNodespace(nodespaceCreateCallbackFn, nsCreateData);
		};
		$scope.submitForm = submitNodespaceCreateForm;
	}
);

//TODO:  obviously this and CreateNodespaceCtrl need some centralization, because it's silly to have totally separate controllers for edit and create when so much of the code is the same
trplApp.controller('EditNodespaceCtrl',
	function($scope, $stateParams, trplBackendSvc) {
		var nodespaceInfo = $scope.nodespaceInfo = {};
		var updateStatus = $scope.updateStatus = {'encounteredUpdateError': null};
		var createStatus = $scope.createStatus = {'encounteredCreateError': null};
		$scope.submitBtnContentKey = 'edit_ns_submit_btn';
		
		var nodespaceInfoCallbackFn = function(nodespaceViewResult) {
			nodespaceInfo = $scope.nodespaceInfo = nodespaceViewResult.nodespace_info;
		};
		trplBackendSvc.getNodespaceViewInfo(nodespaceInfoCallbackFn, $stateParams.nodespaceId);
		
		var nodespaceEditCallbackFn = function(updateResult) {
			if (updateResult == null) {
				updateStatus.encounteredUpdateError = true;
			} else {
				updateStatus.encounteredUpdateError = Boolean(updateResult.encountered_update_error);
			}
		};
		
		var submitNodespaceEditForm = function() {
			var nsEditData = {'nodespace_id': $stateParams.nodespaceId,
								'nodespace_name': nodespaceInfo.nodespace_name, 
								'nodespace_description': nodespaceInfo.nodespace_description};
			trplBackendSvc.editNodespace(nodespaceEditCallbackFn, nsEditData);
		};
		$scope.submitForm = submitNodespaceEditForm;
	}
);

trplApp.controller('CreateUserInvitationCtrl',
	function($scope, trplBackendSvc) {
		var privilegeInfo = $scope.privilegeInfo = {grantablePrivileges: []};
		var invitationInfo = $scope.invitationInfo = {invitee_email_addr: null, 
														selected_metaspace_privileges: {create_space: false, create_user: false, super: false}, 
														invitation_msg: null};
		var createStatus = $scope.createStatus = {encounteredCreateError: null, statusMessage: null};
		
		var getGrantableMetaspacePrivsCallbackFn = function(privInfo) {
			privilegeInfo.grantablePrivileges = privInfo.grantable_privileges;
		};
		trplBackendSvc.getGrantableMetaspacePrivileges(getGrantableMetaspacePrivsCallbackFn);
		
		var invCreateCallbackFn = function(createResult) {
		//TODO: this basic thing is frequently repeated, abstract this to a helper function and the error message html to a partial
			if (createResult == null) {
				createStatus.encounteredCreateError = true;
			} else {
				createStatus.encounteredCreateError = Boolean(createResult.encountered_create_error);
				createStatus.statusMessage = createResult.status_message;
			}
		};
		
		var submitForm = function() {
			var granted_metaspace_privs = [];
			['create_user', 'create_space', 'super'].forEach(function(priv, idx, arr) {
					if (invitationInfo.selected_metaspace_privileges[priv]) {
						granted_metaspace_privs.push(priv);
					}
				}
			);
			
			invCreateData = {invitee_email_addr: invitationInfo.invitee_email_addr, 
								metaspace_privileges: granted_metaspace_privs,
								invitation_msg: invitationInfo.invitation_msg};
			
			trplBackendSvc.createUserInvitation(invCreateCallbackFn, invCreateData);
		};
		$scope.submitForm = submitForm;
	}
);

trplApp.controller('CreateNodespaceInvitationCtrl',
	function($scope, $stateParams, trplBackendSvc) {
		var privilegeInfo = $scope.privilegeInfo = {grantablePrivileges: []};
		var invitationInfo = $scope.invitationInfo = {invitee_email_addr: null, 
														selected_nodespace_privileges: {contributor: false, editor: false, 
																						moderator: false, admin: false}, 
														invitation_msg: null};
		var createStatus = $scope.createStatus = {encounteredCreateError: null, statusMessage: null};
		
		var getGrantableNodespacePrivsCallbackFn = function(privInfo) {
			privilegeInfo.grantablePrivileges = privInfo.grantable_privileges;
		};
		trplBackendSvc.getGrantableNodespacePrivileges(getGrantableNodespacePrivsCallbackFn, $stateParams.nodespaceId);
		
		var invCreateCallbackFn = function(createResult) {
			if (createResult == null) {
				createStatus.encounteredCreateError = true;
			} else {
				createStatus.encounteredCreateError = Boolean(createResult.encountered_create_error);
				createStatus.statusMessage = createResult.status_message;
			}
		};
		
		var submitForm = function() {
			var granted_nodespace_privs = [];
			['contributor', 'editor', 'moderator', 'admin'].forEach(function(priv, idx, arr) {
					if (invitationInfo.selected_nodespace_privileges[priv]) {
						granted_nodespace_privs.push(priv);
					}
				}
			);
			
			invCreateData = {invitee_email_addr: invitationInfo.invitee_email_addr, 
								nodespace_privileges: granted_nodespace_privs,
								invitation_msg: invitationInfo.invitation_msg,
								nodespace_id: $stateParams.nodespaceId};
			
			trplBackendSvc.createNodespaceInvitation(invCreateCallbackFn, invCreateData);
		};
		$scope.submitForm = submitForm;
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
