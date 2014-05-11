var trplApp = angular.module('trpl', ['ngResource', 'ui.state', 'jm.i18next']);


i18n.init({fallbackLng: 'en-US', 
			resStore: window.trplLocaleMsgs, 
			dynamicLoad: false});


//any controller name that's used in a comparison should be a constant (e.g. used in a comparison in a 
//function that returns actual controller functions which vary based on controller name, as in user list)
//TODO: maybe all controller names should be constants?  these just get re-used more than most, so it made more sense here.
var userListCtrlNames = {all: 'UserListAllCtrl',
					nodespace: 'UserListNodespaceCtrl',
					nodespaceAdmin: 'UserListNodespaceAdminCtrl',
					nodespaceAbsent: 'UserListNodespaceAbsentCtrl'};

var editUserInfoCtrlNames = {loggedIn: 'EditLoggedInUserInfoCtrl', other: 'EditOtherUserInfoCtrl'};

var changePasswordCtrlNames = {loggedIn: 'ChangePasswordLoggedInUserCtrl', other: 'ChangePasswordOtherUserCtrl'};

//TODO: maybe all constants should just be in a trplConstants dict that's not a trplApp value.  can't 
//inject the value in all places, and the current approach of sometimes using trplConstants is inconsistent.
//though it is nice to be able to inject it where possible.
//TODO: should avoid also defining rootPath here, since it's already defined in python
trplApp.value('trplConstants', {rootPath: '/tripel',
								dateFormat: 'yyyy-MM-dd HH:mm:ss Z',
								statusTypeError: 'error',
								statusTypeSuccess: 'success',
								statusTypeWarning: 'warning',
								userListCtrlNames: userListCtrlNames,
								editUserInfoCtrlNames: editUserInfoCtrlNames,
								changePasswordCtrlNames: changePasswordCtrlNames});

trplApp.value('trplEvents', {selectNodespace: 'selectNodespace',
								selectUser: 'selectUser',
								userEdited: 'refreshUserList',
								userAccessRevoked: 'userAccessRevoked',
								userAccessGranted: 'userAccessGranted',
								nodespaceEdited: 'refreshNodespaceList'});


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
					controller: userListCtrlNames.nodespaceAdmin,
					templateUrl: 'static/ng_partials/user_list_nodespace.html'
				})
			.state('appView.metaspaceCmds.nodespaceListAll.selectNodespace.userList.selectUser', {
					url: '/:userId',
					controller: 'NodespaceUserAccessAlterCtrl',
					templateUrl: 'static/ng_partials/nodespace_alter_access.html'
				})
			.state('appView.metaspaceCmds.nodespaceListAll.selectNodespace.nodespaceGrantAccess', {
					url: '/nodespace_grant_access',
					controller: userListCtrlNames.nodespaceAbsent,
					templateUrl: 'static/ng_partials/user_list_nodespace.html'
				})
			.state('appView.metaspaceCmds.nodespaceListAll.selectNodespace.nodespaceGrantAccess.selectUser', {
					url: '/:userId',
					controller: 'NodespaceUserAccessGrantCtrl',
					templateUrl: 'static/ng_partials/nodespace_alter_access.html'
				})
			.state('appView.metaspaceCmds.userListAll', {
					url: '/users',
					controller: userListCtrlNames.all,
					templateUrl: 'static/ng_partials/user_list_metaspace.html'
				})
			.state('appView.metaspaceCmds.userListAll.selectUser', {
					url: '/:userId',
					controller: 'SelectUserCtrl',
					templateUrl: 'static/ng_partials/user_view_msadmin.html'
				})
			.state('appView.metaspaceCmds.userListAll.selectUser.editUserInfo', {
					url: '/user_info_edit',
					controller: editUserInfoCtrlNames.other,
					templateUrl: 'static/ng_partials/user_info_edit.html'
				})
			.state('appView.metaspaceCmds.userListAll.selectUser.changeUserPassword', {
					url: '/user_change_password',
					controller: changePasswordCtrlNames.other,
					templateUrl: 'static/ng_partials/user_change_password.html'
				})
			.state('appView.metaspaceCmds.userListAll.selectUser.editMetaspaceAccess', {
					url: '/user_metaspace_access_edit',
					controller: 'MetaspaceUserAccessEditCtrl',
					templateUrl: 'static/ng_partials/user_metaspace_access_edit.html'
				})
			
			.state('appView.metaspaceCmds.userListAll.selectUser.viewSecurityAuditLog', {
					url: '/user_metaspace_security_audit_log',
					controller: '',
					templateUrl: 'static/ng_partials/user_metaspace_security_audit_log.html'
				})
			
			.state('appView.manageLoggedInUser', {
					url: '/manage_logged_in_user',
					templateUrl: 'static/ng_partials/manage_logged_in_user.html'
				})
			.state('appView.manageLoggedInUser.editUserInfo', {
					url: '/user_info_edit',
					controller: editUserInfoCtrlNames.loggedIn,
					templateUrl: 'static/ng_partials/user_info_edit.html'
				})
			.state('appView.manageLoggedInUser.changeUserPassword', {
					url: '/user_change_password',
					controller: changePasswordCtrlNames.loggedIn,
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
					controller: userListCtrlNames.nodespace,
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
		//TODO: isAllowedToUse needs to take params
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
		};
		
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
		
		//TODO: currently there's a minor inconsistency, where get* methods take explicit param values for each 
		//field, and post* methods take an object.  might want to make this the same for both.  inclined to make them 
		//all take explicit param lists.
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
		
		this.getNodespaceAbsentUsers = function(callbackFn, nodespaceId) {
			return this.getObjList(callbackFn, '/user_list_nodespace_absent', {nodespace_id: nodespaceId});
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
		
		this.editNodespace = function(callbackFn, nodespaceUpdData) {
			return this.postReq(callbackFn, '/nodespace_edit', nodespaceUpdData);
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
		
		this.getNodespaceAccessInfo = function(callbackFn, nodespaceId, editedUserId) {
			return this.getObj(callbackFn, '/nodespace_access_edit_form', {nodespace_id: nodespaceId, edited_user_id: editedUserId});
		};
		
		this.updateNodespaceAccess = function(callbackFn, nodespaceAccessUpdData) {
			return this.postReq(callbackFn, '/nodespace_access_edit', nodespaceAccessUpdData);
		};
		
		this.revokeNodespaceAccess = function(callbackFn, nodespaceAccessDelData) {
			return this.postReq(callbackFn, '/nodespace_access_revoke', nodespaceAccessDelData);
		};
		
		this.grantNodespaceAccess = function(callbackFn, nodespaceAccessGrantData) {
			return this.postReq(callbackFn, '/nodespace_access_grant', nodespaceAccessGrantData);
		};
		
		this.updateMetaspaceAccess = function(callbackFn, metaspaceAccessUpdData) {
			return this.postReq(callbackFn, '/metaspace_access_edit', metaspaceAccessUpdData);
		};
		
		this.getMetaspaceAccessInfo = function(callbackFn, userId) {
			return this.getObj(callbackFn, '/metaspace_access_edit_form', {edited_user_id: userId});
		};
	}
);

trplApp.service('paneListSvc', 
	function(trplBackendSvc, $stateParams) {
		this.getPaneList = function(paneListType) {
			switch(paneListType) {
				//TODO: urlHashBase values should come from state info so we're not repeating the definition here
				case 'app-views':
					var urlHashBase = '#/app_view/';
					var panes = [{title: i18n.t('metaspace_command_list_smry'), url: urlHashBase+'metaspace_cmds', isSelected: false, isUsable: false},
							{title: i18n.t('manage_logged_in_user_tab_name'), url: urlHashBase+'manage_logged_in_user', isSelected: false, isUsable: true},
							{title: i18n.t('accessible_nodespaces_tab_name'), url: urlHashBase+'nodespaces_accessible', isSelected: false, isUsable: true}];
					
					var callbackFn = function(isAllowedToUseMetaspaceCmds) {
						panes[0].isUsable = isAllowedToUseMetaspaceCmds;
					};
					
					trplBackendSvc.isAllowedToUse('metaspace_command_list', callbackFn);
					
					return panes;
					
				case 'metaspace-commands':
					var urlHashBase = '#/app_view/metaspace_cmds/';
					var panes = [{title: i18n.t('nodespace_create_form_page_name'), url: urlHashBase+'nodespace_create', isSelected: false, isUsable: false},
							{title: i18n.t('user_invitation_create_form_page_name'), url: urlHashBase+'user_invitation_create', isSelected: false, isUsable: false},
							{title: i18n.t('nodespace_list_all_page_name'), url: urlHashBase+'nodespaces_all', isSelected: false, isUsable: false},
							{title: i18n.t('user_list_all_page_name'), url: urlHashBase+'users', isSelected: false, isUsable: false}];
					
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
					var urlHashBase = '#/app_view/manage_logged_in_user/';
					var panes = [{title: i18n.t('user_info_edit_form_page_name'), url: urlHashBase+'user_info_edit', isSelected: false, isUsable: true},
							{title: i18n.t('user_change_pass_form_page_name'), url: urlHashBase+'user_change_password', isSelected: false, isUsable: true}];
					
					return panes;
				
				case 'nodespace-view':
					var urlHashBase = '#/app_view/nodespaces_accessible/' + $stateParams.nodespaceId + '/';
					var panes = [{title: i18n.t('nodespace_browse_tab_label'), url: urlHashBase+'browse_nodes', isSelected: false, isUsable: true},
								{title: i18n.t('nodespace_edit_form_page_name'), url: urlHashBase+'nodespace_info_edit', isSelected: false, isUsable: false},
								{title: i18n.t('nodespace_user_list_tab_label'), url: urlHashBase+'user_list_nodespace', isSelected: false, isUsable: false},
								{title: i18n.t('nodespace_invitation_create_form_page_name'), url: urlHashBase+'nodespace_invitation_create', isSelected: false, isUsable: false}];
					
					var callbackFn = function(nodespaceViewResult) {
						var nodespaceViewCmdPerms = nodespaceViewResult.perms_for_user;
						panes[1].isUsable = nodespaceViewCmdPerms['is_allowed_to_edit_nodespace'];
						panes[2].isUsable = nodespaceViewCmdPerms['is_allowed_to_list_nodespace_users'];
						panes[3].isUsable = nodespaceViewCmdPerms['is_allowed_to_invite_nodespace_users'];
					};
					
					trplBackendSvc.getNodespaceViewInfo(callbackFn, $stateParams.nodespaceId);
					
					return panes;
				
				case 'nodespace-view-admin':
					var urlHashBase = '#/app_view/metaspace_cmds/nodespaces_all/' + $stateParams.nodespaceId + '/';
					var panes = [{title: i18n.t('nodespace_edit_form_page_name'), url: urlHashBase+'nodespace_info_edit', isSelected: false, isUsable: false},
								{title: i18n.t('nodespace_user_list_tab_label'), url: urlHashBase+'user_list_nodespace', isSelected: false, isUsable: false},
								{title: i18n.t('nodespace_grant_access_tab_label'), url: urlHashBase+'nodespace_grant_access', isSelected: false, isUsable: false}];
					
					var callbackFn = function(nodespaceViewResult) {
						var nodespaceViewCmdPerms = nodespaceViewResult.perms_for_user;
						panes[0].isUsable = nodespaceViewCmdPerms['is_allowed_to_edit_nodespace'];
						panes[1].isUsable = nodespaceViewCmdPerms['is_allowed_to_list_nodespace_users'];
						panes[2].isUsable = nodespaceViewCmdPerms['is_allowed_to_invite_nodespace_users'];
					};
					
					trplBackendSvc.getNodespaceViewInfo(callbackFn, $stateParams.nodespaceId);
					
					return panes;
				
				case 'user-view-admin':
					var urlHashBase = '#/app_view/metaspace_cmds/users/' + $stateParams.userId + '/';
					/*TODO: make the perm checks work and then uncomment this and kill the panes declaration that sets isUsable to true
					var panes = [{title: i18n.t('user_info_edit_form_page_name'), url: urlHashBase+'user_info_edit', isSelected: false, isUsable: false},
								{title: i18n.t('user_change_pass_form_page_name'), url: urlHashBase+'user_change_password', isSelected: false, isUsable: false},
								{title: i18n.t('edit_usr_metaspace_privs_link_disp_txt'), url: urlHashBase+'user_metaspace_access_edit', isSelected: false, isUsable: false},
								{title: i18n.t('view_usr_security_audit_log_link_disp_txt'), url: urlHashBase+'user_metaspace_security_audit_log', isSelected: false, isUsable: false}];
					
					var callbackFn = function(isAllowedToUseCmd, pane) {
						pane.isUsable = isAllowedToUseCmd;
					};
					
					['user_info_edit', 'user_change_password', 'user_metaspace_access_edit', 'user_metaspace_security_audit_log'].forEach(function(cmdName, idx, arr) {
							var paneCallbackFn = function(isAllowedToUseCmd) { callbackFn(isAllowedToUseCmd, panes[idx]); };
							//trplBackendSvc.isAllowedToUse(cmdName, paneCallbackFn);
						}
					);
					*/
					var panes = [{title: i18n.t('user_info_edit_form_page_name'), url: urlHashBase+'user_info_edit', isSelected: false, isUsable: true},
								{title: i18n.t('user_change_pass_form_page_name'), url: urlHashBase+'user_change_password', isSelected: false, isUsable: true},
								{title: i18n.t('edit_usr_metaspace_privs_link_disp_txt'), url: urlHashBase+'user_metaspace_access_edit', isSelected: false, isUsable: true},
								{title: i18n.t('view_usr_security_audit_log_link_disp_txt'), url: urlHashBase+'user_metaspace_security_audit_log', isSelected: false, isUsable: true}];
					
					return panes
				
				default:
					return [];
			}
		};
	}
);


//TODO: refactor ad-hoc status messages to use this and the corresponding partial
var getOperationStatusMsgCallbackFn = function(statusMsgInfoObj, trplConstants, msgContentKeys, useMsgContentKeys) {
	return function(opResult) {
		statusMsgInfoObj.shouldShowMsg = true;
		if (opResult == null) {
			statusMsgInfoObj.statusType = trplConstants.statusTypeError;
		} else {
			statusMsgInfoObj.statusType = (opResult.encountered_update_error == true) ? trplConstants.statusTypeError : trplConstants.statusTypeSuccess;
		}
		
		if (!useMsgContentKeys && opResult.status_message != undefined) {
			statusMsgInfoObj.statusMsg = opResult.status_message;
		} else {
			if (statusMsgInfoObj.statusType == trplConstants.statusTypeError) {
				statusMsgInfoObj.statusMsg = i18n.t(msgContentKeys.failureContentKey);
			} else {
				statusMsgInfoObj.statusMsg = i18n.t(msgContentKeys.successContentKey);
			}
		}
	};
};
		
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

var getUnselectRowFn = function(tableListDataObj, unselectUrlHash) {
	return function() {
		tableListDataObj.selectedRowId = null;
		window.location.hash = unselectUrlHash;
	}
};

//TODO: apply this centralization to other places with checkboxes
//useful for turning a list into selected checkboxes when a map of keys to boolean values provides the ng-model mappings for a checkbox list
var setBooleanKeysFromList = function(booleanObj, enabledList) {
	Object.keys(booleanObj).forEach(function(elt, idx, arr) {
			booleanObj[elt] = false;
		}
	);
	enabledList.forEach(function(elt, idx, arr) {
			booleanObj[elt] = true;
		}
	);
};

//useful for turning a list of checkbox values into a list of the selected checkboxes, assuming a map of boolean values to keys determines which boxes are checked
var getListFromBooleanKeys = function(booleanObj) {
	var enabledList = [];
	Object.keys(booleanObj).forEach(function(key, idx, arr) {
			if (booleanObj[key]) {
				enabledList.push(key);
			}
		}
	);
	
	return enabledList;
};


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

var getNodespaceListCtrlFn = function(urlHashBase, nodespaceListFnName) {
	//note that the function returned here assumes it'll get its params injected by angular upon invocation.  it's intended to be used to build controllers.
	return function($scope, trplBackendSvc, trplEvents) {
		$scope.urlHashBase = urlHashBase;
		
		var nodespaceListData = $scope.nodespaceListData = {selectedRowId: null, rowList: null};
		var callbackFn = getTableListCallbackFn(nodespaceListData);
		trplBackendSvc[nodespaceListFnName](callbackFn);
		
		var selectNodespaceFn = getSelectRowFn(nodespaceListData);
		$scope.$on(trplEvents.selectNodespace, selectNodespaceFn);
		
		var unselectNodespaceFn = getUnselectRowFn(nodespaceListData, urlHashBase);
		$scope.unselectNodespace = unselectNodespaceFn;
		
		var listRefreshFn = function(eventObj, nodespaceId) { 
			trplBackendSvc[nodespaceListFnName](callbackFn);
		};
		$scope.$on(trplEvents.nodespaceEdited, listRefreshFn);
	};
};
trplApp.controller('NodespaceListAllCtrl', getNodespaceListCtrlFn('#/app_view/metaspace_cmds/nodespaces_all', 'getAllNodespaces'));
trplApp.controller('NodespaceListAccessibleCtrl', getNodespaceListCtrlFn('#/app_view/nodespaces_accessible', 'getAccessibleNodespaces'));

trplApp.controller('SelectNodespaceCtrl',
	function($scope, $stateParams, trplEvents) {
		$scope.$emit(trplEvents.selectNodespace, $stateParams.nodespaceId);
	}
);

function getUserListCtrlFn(controllerName) {
	//note that the function returned here assumes it'll get its params injected by angular upon invocation.  it's intended to be used to build controllers.
	return function($scope, $stateParams, $filter, trplBackendSvc, trplConstants, trplEvents) {
		switch(controllerName) {
			case trplConstants.userListCtrlNames.all:
				$scope.urlHashBase = '#/app_view/metaspace_cmds/users';
				break;
			case trplConstants.userListCtrlNames.nodespace:
				$scope.urlHashBase = '#/app_view/nodespaces_accessible/'+$stateParams.nodespaceId+'/user_list_nodespace';
				break;
			case trplConstants.userListCtrlNames.nodespaceAdmin:
				$scope.urlHashBase = '#/app_view/metaspace_cmds/nodespaces_all/'+$stateParams.nodespaceId+'/user_list_nodespace';
				break;
			case trplConstants.userListCtrlNames.nodespaceAbsent:
				$scope.urlHashBase = '#/app_view/metaspace_cmds/nodespaces_all/'+$stateParams.nodespaceId+'/nodespace_grant_access';
				break;
			default:
				$scope.urlHashBase = '#/';
		}
		
		$scope.dateFormat = trplConstants.dateFormat;
		
		var statusMsgInfo = $scope.statusMsgInfo = {shouldShowMsg: false, statusType: null, statusMsg: ''};
		
		
		var userListData = $scope.userListData = {selectedRowId: null, rowList: null};
		var callbackFn = function(userList) {
			userListData.rowList = userList;
			
			if (userListData.rowList != null) {
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
			}
		};
		
		var listRefreshFn;
		switch (controllerName) {
			case trplConstants.userListCtrlNames.all:
				listRefreshFn = function() { trplBackendSvc.getAllUsers(callbackFn); };
				break;
			case trplConstants.userListCtrlNames.nodespaceAbsent:
				listRefreshFn = function() { trplBackendSvc.getNodespaceAbsentUsers(callbackFn, $stateParams.nodespaceId); };
				break;
			case trplConstants.userListCtrlNames.nodespace:
			case trplConstants.userListCtrlNames.nodespaceAdmin:
				listRefreshFn = function() { trplBackendSvc.getNodespaceUsers(callbackFn, $stateParams.nodespaceId); };
				break;
		}
		
		
		var selectUserFn = getSelectRowFn(userListData);
		
		var unselectUserFn = getUnselectRowFn(userListData, $scope.urlHashBase);
		
		var refreshListAndUnselectUserFn = function() {
			listRefreshFn();
			unselectUserFn();
		};
		
		var grantStatusMsgContentKeys = {successContentKey: 'nodespace_access_grant_success_blurb', failureContentKey: 'nodespace_access_grant_failure_blurb'};
		var grantStatusMsgCallbackFn = getOperationStatusMsgCallbackFn(statusMsgInfo, trplConstants, grantStatusMsgContentKeys, true);
		var showAccessGrantedStatusFn = function(eventObj, userId, grantResult) {
			if (grantResult.encountered_update_error == false) {
				refreshListAndUnselectUserFn();
				grantStatusMsgCallbackFn(grantResult);
			}
		};
		
		var delStatusMsgContentKeys = {successContentKey: 'nodespace_access_revoke_success_blurb', failureContentKey: 'nodespace_access_revoke_failure_blurb'};
		var delStatusMsgCallbackFn = getOperationStatusMsgCallbackFn(statusMsgInfo, trplConstants, delStatusMsgContentKeys, true);
		var showAccessRevokedStatusFn = function(eventObj, userId, delResult) {
			if (delResult.encountered_update_error == false) {
				refreshListAndUnselectUserFn();
				delStatusMsgCallbackFn(delResult);
			}
		};
		
		
		$scope.unselectUser = unselectUserFn;
		
		$scope.$on(trplEvents.selectUser, selectUserFn);
		$scope.$on(trplEvents.userAccessGranted, showAccessGrantedStatusFn);
		$scope.$on(trplEvents.userAccessRevoked, showAccessRevokedStatusFn);
		
		
		listRefreshFn();
	};
}
//register each type of user list controller
[userListCtrlNames.all, userListCtrlNames.nodespace, userListCtrlNames.nodespaceAdmin, userListCtrlNames.nodespaceAbsent].forEach(
	function(val, idx, arr) {
		trplApp.controller(val, getUserListCtrlFn(val));
	}
);

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

function getEditUserInfoCtrlFn(controllerName) {
	return function($scope, $stateParams, trplBackendSvc, trplConstants) {
		var userInfo = $scope.userInfo = {};
		var statusMsgInfo = $scope.statusMsgInfo = {shouldShowMsg: false, statusType: null, statusMsg: ''};
		
		var statusMsgContentKeys = {successContentKey: 'user_info_edit_success_msg', failureContentKey: 'user_info_edit_error_msg'};
		var statusMsgCallbackFn = getOperationStatusMsgCallbackFn(statusMsgInfo, trplConstants, statusMsgContentKeys, true);
		
		var userInfoCallbackFn = function(userInfoResult) {
			userInfo = $scope.userInfo = userInfoResult;
		};
		
		var authStatusCallbackFn = function(authInfo) {
			trplBackendSvc.getUserViewInfo(userInfoCallbackFn, authInfo.user_id);
		};
		
		var submitEditForm = function() {
			var userUpdData = {'edited_user_id': userInfo.user_id,
								'username': userInfo.username,
								'email_addr': userInfo.email_addr,
								'user_statement': userInfo.user_statement};
			trplBackendSvc.updateUserInfo(statusMsgCallbackFn, userUpdData);
		};
		$scope.submitEditForm = submitEditForm;
		
		switch (controllerName) {
			case trplConstants.editUserInfoCtrlNames.loggedIn:
				//the fn call to get the user info will be invoked by this call to get the auth info for the logged in user
				trplBackendSvc.getAuthStatus(authStatusCallbackFn);
				break;
			case trplConstants.editUserInfoCtrlNames.other:
				trplBackendSvc.getUserViewInfo(userInfoCallbackFn, $stateParams.userId);
				break;
		}
	};
}
//register each type of edit user controller
[editUserInfoCtrlNames.loggedIn, editUserInfoCtrlNames.other].forEach(
	function(val, idx, arr) {
		trplApp.controller(val, getEditUserInfoCtrlFn(val));
	}
);

function getChangePasswordCtrl(controllerName) {
	return 	function($scope, $stateParams, trplBackendSvc, trplConstants) {
		var pwInfo = $scope.pwInfo = {};
		var statusMsgInfo = $scope.statusMsgInfo = {shouldShowMsg: false, statusType: null, statusMsg: ''};
		
		var statusMsgContentKeys = {successContentKey: 'user_password_edit_success_msg', failureContentKey: 'user_password_edit_error_msg'};
		var statusMsgCallbackFn = getOperationStatusMsgCallbackFn(statusMsgInfo, trplConstants, statusMsgContentKeys, true);
		
		var authStatusCallbackFn = function(authInfo) {
			pwInfo.edited_user_id = authInfo.user_id;
		};
		
		switch (controllerName) {
			case trplConstants.changePasswordCtrlNames.loggedIn:
				trplBackendSvc.getAuthStatus(authStatusCallbackFn);
				break;
			case trplConstants.changePasswordCtrlNames.other:
				pwInfo.edited_user_id = $stateParams.userId;
				break;
		}
		
		var submitPasswordChangeForm = function() {
			var pwUpdData = {'edited_user_id': pwInfo.edited_user_id,
								'editing_user_cleartext_password': pwInfo.editing_user_cleartext_password,
								'cleartext_password_1': pwInfo.cleartext_password_1,
								'cleartext_password_2': pwInfo.cleartext_password_2};
			trplBackendSvc.updateUserPassword(statusMsgCallbackFn, pwUpdData);
		};
		$scope.submitPasswordChangeForm = submitPasswordChangeForm;
	};
}
//register each type of change password controller
[changePasswordCtrlNames.loggedIn, changePasswordCtrlNames.other].forEach(
	function(val, idx, arr) {
		trplApp.controller(val, getChangePasswordCtrl(val));
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
	function($scope, $stateParams, trplBackendSvc, trplEvents) {
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
			
			if (!updateStatus.encounteredUpdateError) {
				$scope.$emit(trplEvents.nodespaceEdited, $stateParams.nodespaceId);
			}
		};
		
		var submitNodespaceEditForm = function() {
			var nsUpdData = {'nodespace_id': $stateParams.nodespaceId,
								'nodespace_name': nodespaceInfo.nodespace_name, 
								'nodespace_description': nodespaceInfo.nodespace_description};
			trplBackendSvc.editNodespace(nodespaceEditCallbackFn, nsUpdData);
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
			
			var invCreateData = {invitee_email_addr: invitationInfo.invitee_email_addr, 
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
		var invitationInfo = $scope.invitationInfo = {inviteeEmailAddr: null, 
														selectedNodespacePrivileges: {contributor: false, editor: false, 
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
					if (invitationInfo.selectedNodespacePrivileges[priv]) {
						granted_nodespace_privs.push(priv);
					}
				}
			);
			
			var invCreateData = {invitee_email_addr: invitationInfo.inviteeEmailAddr, 
								nodespace_privileges: granted_nodespace_privs,
								invitation_msg: invitationInfo.invitation_msg,
								nodespace_id: $stateParams.nodespaceId};
			
			trplBackendSvc.createNodespaceInvitation(invCreateCallbackFn, invCreateData);
		};
		$scope.submitForm = submitForm;
	}
);

trplApp.controller('NodespaceUserAccessAlterCtrl',
	function($scope, $stateParams, trplBackendSvc, trplEvents, trplConstants) {
		$scope.$emit(trplEvents.selectUser, $stateParams.userId);
		
		$scope.isAlterAccess = true;
		
		$scope.localContent = {accessEnabledOption: i18n.t('ns_enabled_desc'), 
							accessDisabledOption: i18n.t('ns_disabled_desc'),
							headerContentKey: 'nodespace_access_edit_form_page_name',
							updButtonContentKey: 'upd_nodespace_access_submit_btn'};
		
		//TODO: grantablePrivileges here actually has a similar problem to the grant access ctrl: if the editing user's 
		//not an admin in the nodespace, the list stays empty.  but presumably they're a metaspace admin if they're here, so
		//they should be able to grant whatever.
		var privilegeInfo = $scope.privilegeInfo = {grantablePrivileges: [], 
													selectedNodespacePrivileges: {contributor: false, editor: false, 
																					moderator: false, admin: false},
													isEnabled: false};
		
		var statusMsgInfo = $scope.statusMsgInfo = {shouldShowMsg: false, statusType: null, statusMsg: ''};
		
		var getNodespaceAccessInfoCallbackFn = function(privInfo) {
			privilegeInfo.grantablePrivileges = privInfo.grantable_privileges;
			setBooleanKeysFromList(privilegeInfo.selectedNodespacePrivileges, privInfo.current_privileges);
			privilegeInfo.isEnabled = privInfo.is_enabled;
		};
		trplBackendSvc.getNodespaceAccessInfo(getNodespaceAccessInfoCallbackFn, $stateParams.nodespaceId, $stateParams.userId);
		
		var updStatusMsgContentKeys = {successContentKey: 'nodespace_access_update_success_blurb', failureContentKey: 'nodespace_access_update_failure_blurb'};
		var updStatusMsgCallbackFn = getOperationStatusMsgCallbackFn(statusMsgInfo, trplConstants, updStatusMsgContentKeys, true);
		var submitUpdAccessForm = function() {
			var grantedNodespacePrivs = getListFromBooleanKeys(privilegeInfo.selectedNodespacePrivileges);
			
			var nodespaceAccessUpdData = {nodespace_id: $stateParams.nodespaceId, 
										edited_user_id: $stateParams.userId,
										nodespace_privileges: grantedNodespacePrivs,
										is_enabled: privilegeInfo.isEnabled};
			
			var updCallbackFn = function(updResult) {
				updStatusMsgCallbackFn(updResult);
				$scope.$emit(trplEvents.userEdited, $stateParams.userId);
			};
			
			trplBackendSvc.updateNodespaceAccess(updCallbackFn, nodespaceAccessUpdData);
		};
		$scope.submitUpdAccessForm = submitUpdAccessForm;
		
		var delStatusMsgContentKeys = {successContentKey: 'nodespace_access_revoke_success_blurb', failureContentKey: 'nodespace_access_revoke_failure_blurb'};
		var delStatusMsgCallbackFn = getOperationStatusMsgCallbackFn(statusMsgInfo, trplConstants, delStatusMsgContentKeys, true);
		var submitDelAccessForm = function() {
			nodespaceAccessDelData = {nodespace_id: $stateParams.nodespaceId, edited_user_id: $stateParams.userId};
			
			var delCallbackFn = function(delResult) {
				delStatusMsgCallbackFn(delResult);
				$scope.$emit(trplEvents.userAccessRevoked, $stateParams.userId, delResult);
			};
			
			trplBackendSvc.revokeNodespaceAccess(delCallbackFn, nodespaceAccessDelData);
		};
		$scope.submitDelAccessForm = submitDelAccessForm;
	}
);

trplApp.controller('NodespaceUserAccessGrantCtrl',
	function($scope, $stateParams, trplBackendSvc, trplEvents, trplConstants) {
		$scope.$emit(trplEvents.selectUser, $stateParams.userId);
		
		$scope.isAlterAccess = false;
		
		$scope.localContent = {accessEnabledOption: i18n.t('ns_enabled_desc'), 
							accessDisabledOption: i18n.t('ns_disabled_desc'),
							headerContentKey: 'nodespace_access_grant_form_page_name',
							updButtonContentKey: 'grant_nodespace_access_submit_btn'};
		
		//TODO: really, we should get the list of grantable privileges from a perm check.  but this can only be used by a super-user,
		//and the backend method that actually grants access won't let improper access be granted anyway.  no easy/clean way to get this via 
		//perm check at the moment.
		var privilegeInfo = $scope.privilegeInfo = {grantablePrivileges: ['contributor', 'editor', 'moderator', 'admin'], 
													selectedNodespacePrivileges: {contributor: false, editor: false, 
																					moderator: false, admin: false},
													isEnabled: false};
		
		var statusMsgInfo = $scope.statusMsgInfo = {shouldShowMsg: false, statusType: null, statusMsg: ''};
		
		var grantStatusMsgContentKeys = {successContentKey: 'nodespace_access_grant_success_blurb', failureContentKey: 'nodespace_access_grant_failure_blurb'};
		var grantStatusMsgCallbackFn = getOperationStatusMsgCallbackFn(statusMsgInfo, trplConstants, grantStatusMsgContentKeys, true);
		var submitUpdAccessForm = function() {
			var grantedNodespacePrivs = getListFromBooleanKeys(privilegeInfo.selectedNodespacePrivileges);
			
			nodespaceAccessUpdData = {nodespace_id: $stateParams.nodespaceId, 
										edited_user_id: $stateParams.userId,
										nodespace_privileges: grantedNodespacePrivs,
										is_enabled: privilegeInfo.isEnabled};
										
			var grantCallbackFn = function(grantResult) {
				grantStatusMsgCallbackFn(grantResult);
				$scope.$emit(trplEvents.userAccessGranted, $stateParams.userId, grantResult);
			};
			
			trplBackendSvc.grantNodespaceAccess(grantCallbackFn, nodespaceAccessUpdData);
		};
		$scope.submitUpdAccessForm = submitUpdAccessForm;
	}
);

trplApp.controller('MetaspaceUserAccessEditCtrl',
	function($scope, $stateParams, trplBackendSvc, trplEvents, trplConstants) {
		$scope.localContent = {accessEnabledOption: i18n.t('ms_enabled_desc'), 
							accessDisabledOption: i18n.t('ms_disabled_desc'),
							headerContentKey: 'edit_usr_metaspace_privs_link_disp_txt',
							updButtonContentKey: 'update_ms_privs_submit_btn'};
		
		var privilegeInfo = $scope.privilegeInfo = {grantablePrivileges: [], 
													selectedMetaspacePrivileges: {create_space: false, create_user: false, super: false},
													isEnabled: false};
													
		var statusMsgInfo = $scope.statusMsgInfo = {shouldShowMsg: false, statusType: null, statusMsg: ''};
		
		var getMetaspaceAccessInfoCallbackFn = function(privInfo) {
			privilegeInfo.grantablePrivileges = privInfo.grantable_privileges;
			setBooleanKeysFromList(privilegeInfo.selectedMetaspacePrivileges, privInfo.current_privileges);
			privilegeInfo.isEnabled = privInfo.is_enabled;
		};
		trplBackendSvc.getMetaspaceAccessInfo(getMetaspaceAccessInfoCallbackFn, $stateParams.userId);
		
		var updStatusMsgContentKeys = {successContentKey: 'metaspace_access_update_success_blurb', failureContentKey: 'metaspace_access_update_failure_blurb'};
		var updStatusMsgCallbackFn = getOperationStatusMsgCallbackFn(statusMsgInfo, trplConstants, updStatusMsgContentKeys, true);
		var submitUpdAccessForm = function() {
			var grantedMetaspacePrivs = getListFromBooleanKeys(privilegeInfo.selectedMetaspacePrivileges);
			
			var metaspaceAccessUpdData = {edited_user_id: $stateParams.userId,
											metaspace_privileges: grantedMetaspacePrivs,
											is_enabled: privilegeInfo.isEnabled};
			var updCallbackFn = function(updResult) {
				updStatusMsgCallbackFn(updResult);
			};
			
			trplBackendSvc.updateMetaspaceAccess(updCallbackFn, metaspaceAccessUpdData);
		};
		$scope.submitUpdAccessForm = submitUpdAccessForm;
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

trplApp.directive('statusmessage',
	function() {
		return {
			restrict: 'E',
			replace: true,
			scope: {shouldShowMsg: '@shouldShowMsg', statusType: '@statusType', statusMsg: '@statusMsg'},
			
			templateUrl: 'static/ng_partials/status_message_container.html'
		};
	}
);
