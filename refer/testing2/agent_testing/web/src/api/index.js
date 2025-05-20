import { request } from '@/utils'

export default {
  login: (data) => request.post('/base/access_token', data, { noNeedToken: true }),
  getUserInfo: () => request.get('/base/userinfo'),
  getUserMenu: () => request.get('/base/usermenu'),
  getUserApi: () => request.get('/base/userapi'),
  // profile
  updatePassword: (data = {}) => request.post('/base/update_password', data),
  // users
  getUserList: (params = {}) => request.get('/user/list', { params }),
  getUserById: (params = {}) => request.get('/user/get', { params }),
  createUser: (data = {}) => request.post('/user/create', data),
  updateUser: (data = {}) => request.post('/user/update', data),
  deleteUser: (params = {}) => request.delete(`/user/delete`, { params }),
  resetPassword: (data = {}) => request.post(`/user/reset_password`, data),
  // role
  getRoleList: (params = {}) => request.get('/role/list', { params }),
  createRole: (data = {}) => request.post('/role/create', data),
  updateRole: (data = {}) => request.post('/role/update', data),
  deleteRole: (params = {}) => request.delete('/role/delete', { params }),
  updateRoleAuthorized: (data = {}) => request.post('/role/authorized', data),
  getRoleAuthorized: (params = {}) => request.get('/role/authorized', { params }),
  // menus
  getMenus: (params = {}) => request.get('/menu/list', { params }),
  createMenu: (data = {}) => request.post('/menu/create', data),
  updateMenu: (data = {}) => request.post('/menu/update', data),
  deleteMenu: (params = {}) => request.delete('/menu/delete', { params }),
  // apis
  getApis: (params = {}) => request.get('/api/list', { params }),
  createApi: (data = {}) => request.post('/api/create', data),
  updateApi: (data = {}) => request.post('/api/update', data),
  deleteApi: (params = {}) => request.delete('/api/delete', { params }),
  refreshApi: (data = {}) => request.post('/api/refresh', data),
  // depts
  getDepts: (params = {}) => request.get('/dept/list', { params }),
  createDept: (data = {}) => request.post('/dept/create', data),
  updateDept: (data = {}) => request.post('/dept/update', data),
  deleteDept: (params = {}) => request.delete('/dept/delete', { params }),
  // auditlog
  getAuditLogList: (params = {}) => request.get('/auditlog/list', { params }),
  // projects
  getProjts: (params = {}) => request.get('/project/list', { params }),
  createProj: (data = {}) => request.post('/project/create', data),
  updateProj: (data = {}) => request.post('/project/update', data),
  deleteProj: (params = {}) => request.delete('/project/delete', { params }),
  // requirements
  // getReqs: (params = {}) => request.get('/requirement/list', { params }),
  getRequirementsList: (params = {}) => request.get('/requirement/list', { params }),
  createRequirement: (data = {}) => request.post('/requirement/create', data),
  updateRequirement: (data = {}) => request.post('/requirement/update', data),
  deleteRequirement: (params = {}) => request.delete('/requirement/delete', { params }),
  chatReq: (data = {}) => request.post('/requirement/chat', data),
  uploadReq: (data = {}) => request.post('/requirement/chat/upload', data),
  // generator
  getGens: (params = {}) => request.get('/dept/list', { params }),
  createGen: (data = {}) => request.post('/dept/create', data),
  updateGen: (data = {}) => request.post('/dept/update', data),
  deleteGen: (params = {}) => request.delete('/dept/delete', { params }),
  // testcases
  getTestCases: (params = {}) => request.get('/testcase/list', { params }),
  createTestCase: (data = {}) => request.post('/testcase/create', data),
  updateTestCase: (data = {}) => request.post('/testcase/update', data),
  deleteTestCase: (params = {}) => request.delete('/testcase/delete', { params }),
   // 新增文件上传方法
  uploadFile: (user_id, file) => {
    const formData = new FormData()
    formData.append('file', file) // 使用'file'作为字段名（更符合单文件语义）
    return request.post(`/agent/upload?user_id=${user_id}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }

}
