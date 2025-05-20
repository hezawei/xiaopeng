<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import { NButton, NForm, NFormItem, NInput, NInputNumber, NPopconfirm, NTreeSelect } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
// import { loginTypeMap, loginTypeOptions } from '@/constant/data'
import api from '@/api'

defineOptions({ name: '需求管理' })

const $table = ref(null)
const queryItems = ref({
  page: 1,      // 添加默认页码
  page_size: 10 // 添加默认页大小
})
// 分页配置
const pagination = reactive({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page) => {
    pagination.page = page
    $table.value?.handleSearch()
  },
  onUpdatePageSize: (pageSize) => {
    pagination.pageSize = pageSize
    pagination.page = 1
    $table.value?.handleSearch()
  }
})
function handleSearch() {
  $table.value?.handleSearch({
    ...queryItems.value,
    page: pagination.page,
    page_size: pagination.pageSize
  })
}
const vPermission = resolveDirective('permission')

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleSave,
  modalForm,
  modalFormRef,
  handleEdit,
  handleDelete,
  handleAdd,
} = useCRUD({
  name: '需求',
  initForm: { order: 0 },
  doCreate: api.createRequirement,
  doUpdate: api.updateRequirement,
  doDelete: api.deleteRequirement,
  refresh: () => $table.value?.handleSearch(),
})

const projOption = ref([])
const isDisabled = ref(false)

onMounted(() => {
  api.getProjts({ page: 1, page_size: 1000 }).then((res) => {
    if (res.data && Array.isArray(res.data)) {
      projOption.value = res.data.map(item => ({
        key: item.id,
        label: item.name,
        value: item.id
      }));
    }
  });
  handleSearch() // 改用新的搜索方法
})

const reqsRules = {
  name: [
    {
      required: true,
      message: '请输入需求名称',
      trigger: ['input', 'blur', 'change'],
    },
  ],
}

async function addReqs() {
  isDisabled.value = false
  handleAdd()
}

const columns = [
  {
    title: '需求名称',
    key: 'name',
    width: 'auto',
    align: 'left',
    ellipsis: { tooltip: true },
  },
  {
    title: '需求描述',
    key: 'description',
    width: 'auto',
    align: 'left',
    ellipsis: { tooltip: true },
  },

  {
    title: '备注',
    key: 'remark',
    align: 'left',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  // {
  //   title: '创建时间',
  //   key: 'created_at',
  //   align: 'center',
  //   width: 'auto',
  //   ellipsis: { tooltip: true },
  // },
  {
    title: '关联项目',
    key: 'project_id',
    width: 'left',
    align: 'center',
    ellipsis: { tooltip: true },
    render(row) {
      if (!projOption.value || projOption.value.length === 0) {
        return '加载中...';
      }
      const project = projOption.value.find(option => option.value === row.project_id);
      return project ? project.label : '未分配';
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 'auto',
    align: 'center',
    fixed: 'right',
    render(row) {
      return [
        withDirectives(
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              style: 'margin-left: 8px;',
              onClick: () => {
                console.log('row', row.id)
                if (row.id === 0) {
                  isDisabled.value = true
                } else {
                  isDisabled.value = false
                }
                handleEdit(row)
              },
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/requirement/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ id: row.id, project_id: row.project_id }, false),
            onNegativeClick: () => {},
          },
          {
            trigger: () =>
              withDirectives(
                h(
                  NButton,
                  {
                    size: 'small',
                    type: 'error',
                    style: 'margin-left: 8px;',
                  },
                  {
                    default: () => '删除',
                    icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                  }
                ),
                [[vPermission, 'delete/api/v1/requirement/delete']]
              ),
            default: () => h('div', {}, '确定删除该需求吗?'),
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <!-- 业务页面 -->
  <CommonPage show-footer title="需求列表">
    <template #action>
      <div>
        <NButton
          v-permission="'post/api/v1/requirement/create'"
          class="float-right mr-15"
          type="primary"
          @click="addReqs"
        >
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新增需求
        </NButton>
      </div>
    </template>
    <!-- 表格 -->
   <CrudTable
    ref="$table"
    v-model:query-items="queryItems"
    :columns="columns"
    :get-data="(params) => api.getRequirementsList({
      ...params,
      page: pagination.page,
      page_size: pagination.pageSize
    })"
    :pagination="pagination"
    remote
    @update:pagination="(val) => Object.assign(pagination, val)"
  >
      <template #queryBar>
        <QueryBarItem label="项目名称" :label-width="80">
          <NTreeSelect
            v-model:value="queryItems.project_id"
            :options="projOption"
            key-field="key"
            label-field="label"
            value-field="value"
            style="width: 200px;"
            placeholder="请选择项目"
            clearable
            default-expand-all
            :disabled="isDisabled"
          ></NTreeSelect>
        </QueryBarItem>
      </template>
    </CrudTable>

    <!-- 新增/编辑 弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSave"
    >
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="modalForm"
        :rules="reqsRules"
      >
      <NFormItem label="关联项目" path="project_id">
          <NTreeSelect
            v-model:value="modalForm.project_id"
            :options="projOption"
            key-field="key"
            label-field="label"
            value-field="value"
            placeholder="请选择项目"
            clearable
            default-expand-all
            :disabled="isDisabled"
          ></NTreeSelect>
        </NFormItem>
        <NFormItem label="需求名称" path="name">
          <NInput v-model:value="modalForm.name" clearable placeholder="请输入需求名称" />
        </NFormItem>
        <NFormItem label="需求内容" path="description">
          <NInput v-model:value="modalForm.description" clearable placeholder="请输入需求内容" />
        </NFormItem>
        <NFormItem label="备注" path="remark">
          <NInput v-model:value="modalForm.remark" type="textarea" clearable />
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>
