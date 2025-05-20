<template>
  <!-- 业务页面 -->
  <CommonPage show-footer title="用例列表">
    <template #action>
      <div>
        <NButton
          v-permission="'post/api/v1/testcase/create'"
          class="float-right mr-15"
          type="primary"
          @click="addCases"
        >
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新增用例
        </NButton>
      </div>
    </template>
    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getTestCases"
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
            @keypress.enter="$table?.handleSearch()"
          ></NTreeSelect>
        </QueryBarItem>
        <QueryBarItem label="需求名称" :label-width="80">
          <NTreeSelect
            v-model:value="queryItems.requirement_id"
            :options="reqsOption"
            key-field="key"
            label-field="label"
            value-field="value"
            style="width: 200px;"
            placeholder="请选择需求名称"
            clearable
            default-expand-all
            :disabled="isDisabled || !queryItems.project_id"
            @keypress.enter="$table?.handleSearch()"
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
    :rules="caseRules"
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
    <NFormItem label="关联需求" path="requirement_id">
      <NTreeSelect
        v-model:value="modalForm.requirement_id"
        :options="reqsOption"
        key-field="key"
        label-field="label"
        value-field="value"
        placeholder="请选择需求"
        clearable
        default-expand-all
        :disabled="isDisabled || !modalForm.project_id"
      ></NTreeSelect>
    </NFormItem>
    <NFormItem label="用例标题" path="title">
      <NInput v-model:value="modalForm.title" clearable placeholder="请输入用例标题" />
    </NFormItem>
    <NFormItem label="用例描述" path="desc">
      <NInput v-model:value="modalForm.desc" clearable placeholder="请输入用例描述" />
    </NFormItem>
    <NFormItem label="前置条件" path="preconditions">
      <NInput v-model:value="modalForm.preconditions" clearable placeholder="请输入前置条件" />
    </NFormItem>
    <NFormItem label="用例步骤" path="steps">
      <div v-for="(step, index) in modalForm.steps" :key="index" style="margin-bottom: 10px;">
        <NInput v-model:value="step.description" placeholder="请输入步骤描述" />
        <NInput v-model:value="step.expected_result" placeholder="请输入预期结果" />
      </div>
      <NButton type="primary" @click="addStep">新增步骤</NButton>
    </NFormItem>
    <NFormItem label="后置条件" path="postconditions">
      <NInput v-model:value="modalForm.postconditions" clearable placeholder="请输入后置条件" />
    </NFormItem>
    <NFormItem label="优先级" path="priority">
      <NSelect
        v-model:value="modalForm.priority"
        :options="[
          { label: '高', value: '高' },
          { label: '中', value: '中' },
          { label: '低', value: '低' },
        ]"
        placeholder="请选择优先级"
      />
    </NFormItem>
    <NFormItem label="用例状态" path="status">
      <NSelect
        v-model:value="modalForm.status"
        :options="[
          { label: '未开始', value: '未开始' },
          { label: '进行中', value: '进行中' },
          { label: '通过', value: '通过' },
          { label: '失败', value: '失败' },
          { label: '阻塞', value: '阻塞' },
        ]"
        placeholder="请选择状态"
      />
    </NFormItem>
    <NFormItem label="用例标签" path="tags">
      <NSelect
        v-model:value="modalForm.tags"
        multiple
        :options="[
          { label: '单元测试', value: '单元测试' },
          { label: '功能测试', value: '功能测试' },
          { label: '集成测试', value: '集成测试' },
          { label: '系统测试', value: '系统测试' },
          { label: '冒烟测试', value: '冒烟测试' },
          { label: '版本验证', value: '版本验证' },
        ]"
        placeholder="请选择标签"
      />
    </NFormItem>
    <NFormItem label="创建者" path="creator">
      <NInput v-model:value="modalForm.creator" clearable placeholder="请输入创建者" />
    </NFormItem>
  </NForm>
</CrudModal>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import { NButton, NForm, NFormItem, NInput, NInputNumber, NPopconfirm, NSelect, NStep, NTreeSelect } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
// import { loginTypeMap, loginTypeOptions } from '@/constant/data'
import api from '@/api'

defineOptions({ name: '用例管理' })

const $table = ref(null)
const queryItems = ref({})
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
  name: '用例',
  initForm: { order: 0 },
  doCreate: api.createTestCase,
  doUpdate: api.updateTestCase,
  doDelete: api.deleteTestCase,
  refresh: () => $table.value?.handleSearch(),
})

const projOption = ref([])
const reqsOption = ref([])
const isDisabled = ref(false)
onMounted(() => {
  api.getProjts({ page: 1, page_size: 1000 }).then((res) => {
    if (res.data && Array.isArray(res.data)) {
      projOption.value = res.data.map(item => ({
        key: item.id,
        label: item.name,
        value: Number(item.id)  // [!code ++] 强制转为数字类型
      }));
    }
  });
  $table.value?.handleSearch()
})

// 根据项目 ID 加载需求列表
const loadRequirementsByProject = async (projectId) => {
    if (typeof projectId !== 'number' || isNaN(projectId)) {
    console.error('Invalid projectId:', projectId);
    reqsOption.value = [];
    return;
  }
  console.log('加载需求列表，项目 ID:', projectId);
  if (!projectId) {
    reqsOption.value = [];
    return;
  }

  try {
    const res = await api.getRequirementsList({ project_id: projectId });
    console.log('接口返回数据:', res);
    if (res.data && Array.isArray(res.data)) {
      reqsOption.value = res.data.map(item => ({
        key: item.id,
        label: item.name,
        value: item.id,
      }));
    } else {
      reqsOption.value = [];
    }
  } catch (error) {
    console.error('加载需求失败:', error);
    reqsOption.value = [];
  }
}
// 监听主查询栏中的项目变化
watch(
  () => queryItems.value.project_id,
  async (newVal) => {
    if (!newVal) {
      reqsOption.value = [];
      queryItems.value.requirement_id = null;
      return;
    }
    await loadRequirementsByProject(Number(newVal)); // [!code ++] 明确传递数字类型
  }
);

// 对弹窗表单的监听同理
watch(
  () => modalForm.value.project_id,
  async (newVal) => {
    if (!newVal) {
      reqsOption.value = [];
      modalForm.value.requirement_id = null;
      return;
    }
    await loadRequirementsByProject(newVal);
  }
);

const caseRules = {
  name: [
    {
      required: true,
      message: '请输入用例名称',
      trigger: ['input', 'blur', 'change'],
    },
  ],
}

async function addCases() {
  isDisabled.value = false
  handleAdd()
}

const addStep = () => {
  if (!modalForm.value.steps) {
    modalForm.value.steps = [];
  }
  modalForm.value.steps.push({
    description: '',
    expected_result: '',
  });
};

const columns = [
  {
    title: '用例ID',
    key: 'id',
    width: 'auto',
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: '用例标题',
    key: 'title',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: '用例描述',
    key: 'desc',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: '前置条件',
    key: 'preconditions',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: '用例步骤',
    key: 'steps',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
    render(row) {
      // 展示步骤列表
      return h('div', {}, row.testcase_steps?.map(step => h('p', {}, step.description)));
    },
  },
  {
    title: '后置条件',
    key: 'postconditions',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: '优先级',
    key: 'priority',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
    render(row) {
      // 根据优先级值显示对应的中文
      const priorityMap = { HIGH: '高', MEDIUM: '中', LOW: '低' };
      return h('span', {}, priorityMap[row.priority]);
    },
  },
  {
    title: '用例状态',
    key: 'status',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
    render(row) {
      // 根据状态值显示对应的中文
      const statusMap = {
        NOT_STARTED: '未开始',
        IN_PROGRESS: '进行中',
        PASSED: '通过',
        FAILED: '失败',
        BLOCKED: '阻塞',
      };
      return h('span', {}, statusMap[row.status]);
    },
  },
  {
    title: '用例标签',
    key: 'tags',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
    render(row) {
      // 展示标签列表
      return h(
        'div',
        {},
        row.tags?.map(tag => h('span', { style: 'margin-right: 5px;' }, tag))
      );
    },
  },
  {
    title: '关联需求',
    key: 'requirement_id',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: '关联项目',
    key: 'project_id',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: '创建者',
    key: 'creator',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: '创建时间',
    key: 'create_at',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
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
                if (row.parent_id === 0) {
                  isDisabled.value = true;
                } else {
                  isDisabled.value = false;
                }
                handleEdit(row);
              },
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/testcase/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ case_id: row.id }, false),
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
                [[vPermission, 'delete/api/v1/testcase/delete']]
              ),
            default: () => h('div', {}, '确定删除该用例吗?'),
          }
        ),
      ];
    },
  },
];
</script>


