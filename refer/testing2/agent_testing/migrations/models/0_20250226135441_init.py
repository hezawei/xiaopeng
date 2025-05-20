from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "api" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "path" VARCHAR(100) NOT NULL  /* API路径 */,
    "method" VARCHAR(6) NOT NULL  /* 请求方法 */,
    "summary" VARCHAR(500) NOT NULL  /* 请求简介 */,
    "tags" VARCHAR(100) NOT NULL  /* API标签 */
) /* API 模型，用于存储系统 API 信息。 */;
CREATE INDEX IF NOT EXISTS "idx_api_created_78d19f" ON "api" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_api_updated_643c8b" ON "api" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_api_path_9ed611" ON "api" ("path");
CREATE INDEX IF NOT EXISTS "idx_api_method_a46dfb" ON "api" ("method");
CREATE INDEX IF NOT EXISTS "idx_api_summary_400f73" ON "api" ("summary");
CREATE INDEX IF NOT EXISTS "idx_api_tags_04ae27" ON "api" ("tags");
CREATE TABLE IF NOT EXISTS "audit_log" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL  /* 用户ID */,
    "username" VARCHAR(64) NOT NULL  DEFAULT '' /* 用户名称 */,
    "module" VARCHAR(64) NOT NULL  DEFAULT '' /* 功能模块 */,
    "summary" VARCHAR(128) NOT NULL  DEFAULT '' /* 请求描述 */,
    "method" VARCHAR(10) NOT NULL  DEFAULT '' /* 请求方法 */,
    "path" VARCHAR(255) NOT NULL  DEFAULT '' /* 请求路径 */,
    "status" INT NOT NULL  DEFAULT -1 /* 状态码 */,
    "response_time" INT NOT NULL  DEFAULT 0 /* 响应时间(单位ms) */
) /* 审计日志模型，用于存储系统操作日志。 */;
CREATE INDEX IF NOT EXISTS "idx_audit_log_created_277f5d" ON "audit_log" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_audit_log_updated_4bb07a" ON "audit_log" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_audit_log_user_id_d5b3c4" ON "audit_log" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_audit_log_usernam_b6341e" ON "audit_log" ("username");
CREATE INDEX IF NOT EXISTS "idx_audit_log_module_a9ee07" ON "audit_log" ("module");
CREATE INDEX IF NOT EXISTS "idx_audit_log_summary_88bf13" ON "audit_log" ("summary");
CREATE INDEX IF NOT EXISTS "idx_audit_log_method_2525a0" ON "audit_log" ("method");
CREATE INDEX IF NOT EXISTS "idx_audit_log_path_39c3ce" ON "audit_log" ("path");
CREATE INDEX IF NOT EXISTS "idx_audit_log_status_60fba5" ON "audit_log" ("status");
CREATE INDEX IF NOT EXISTS "idx_audit_log_respons_1e56a2" ON "audit_log" ("response_time");
CREATE TABLE IF NOT EXISTS "dept" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(20) NOT NULL UNIQUE /* 部门名称 */,
    "desc" VARCHAR(500)   /* 备注 */,
    "is_deleted" INT NOT NULL  DEFAULT 0 /* 软删除标记 */,
    "order" INT NOT NULL  DEFAULT 0 /* 排序 */,
    "parent_id" INT NOT NULL  DEFAULT 0 /* 父部门ID */
) /* 部门模型，用于存储系统部门信息。 */;
CREATE INDEX IF NOT EXISTS "idx_dept_created_4b11cf" ON "dept" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_dept_updated_0c0bd1" ON "dept" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_dept_name_c2b9da" ON "dept" ("name");
CREATE INDEX IF NOT EXISTS "idx_dept_is_dele_466228" ON "dept" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_dept_order_ddabe1" ON "dept" ("order");
CREATE INDEX IF NOT EXISTS "idx_dept_parent__a71a57" ON "dept" ("parent_id");
CREATE TABLE IF NOT EXISTS "dept_closure" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "ancestor" INT NOT NULL  /* 父代 */,
    "descendant" INT NOT NULL  /* 子代 */,
    "level" INT NOT NULL  DEFAULT 0 /* 深度 */
) /* 部门闭包模型，用于存储部门之间的层级关系。 */;
CREATE INDEX IF NOT EXISTS "idx_dept_closur_created_0a8afb" ON "dept_closure" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_dept_closur_updated_d17f94" ON "dept_closure" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_dept_closur_ancesto_cc8afb" ON "dept_closure" ("ancestor");
CREATE INDEX IF NOT EXISTS "idx_dept_closur_descend_77690d" ON "dept_closure" ("descendant");
CREATE INDEX IF NOT EXISTS "idx_dept_closur_level_adb2a9" ON "dept_closure" ("level");
CREATE TABLE IF NOT EXISTS "menu" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(20) NOT NULL  /* 菜单名称 */,
    "remark" JSON   /* 保留字段 */,
    "menu_type" VARCHAR(7)   /* 菜单类型 */,
    "icon" VARCHAR(100)   /* 菜单图标 */,
    "path" VARCHAR(100) NOT NULL  /* 菜单路径 */,
    "order" INT NOT NULL  DEFAULT 0 /* 排序 */,
    "parent_id" INT NOT NULL  DEFAULT 0 /* 父菜单ID */,
    "is_hidden" INT NOT NULL  DEFAULT 0 /* 是否隐藏 */,
    "component" VARCHAR(100) NOT NULL  /* 组件 */,
    "keepalive" INT NOT NULL  DEFAULT 1 /* 存活 */,
    "redirect" VARCHAR(100)   /* 重定向 */
) /* 菜单模型，用于存储系统菜单信息。 */;
CREATE INDEX IF NOT EXISTS "idx_menu_created_b6922b" ON "menu" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_menu_updated_e6b0a1" ON "menu" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_menu_name_b9b853" ON "menu" ("name");
CREATE INDEX IF NOT EXISTS "idx_menu_path_bf95b2" ON "menu" ("path");
CREATE INDEX IF NOT EXISTS "idx_menu_order_606068" ON "menu" ("order");
CREATE INDEX IF NOT EXISTS "idx_menu_parent__bebd15" ON "menu" ("parent_id");
CREATE TABLE IF NOT EXISTS "project" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP /* 创建时间 */,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL UNIQUE /* 项目名称 */,
    "desc" TEXT NOT NULL  /* 项目内容 */
) /* 项目模型，用于存储项目信息。 */;
CREATE INDEX IF NOT EXISTS "idx_project_updated_d3b2ab" ON "project" ("updated_at");
CREATE TABLE IF NOT EXISTS "requirement" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP /* 创建时间 */,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL UNIQUE /* 需求名称 */,
    "content" TEXT NOT NULL  /* 需求内容 */,
    "project_id" INT NOT NULL  /* 关联项目 */,
    "remark" TEXT   /* 备注 */
) /* 需求模型，用于存储需求信息。 */;
CREATE INDEX IF NOT EXISTS "idx_requirement_updated_7195c5" ON "requirement" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_requirement_project_7968bd" ON "requirement" ("project_id");
CREATE TABLE IF NOT EXISTS "role" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(20) NOT NULL UNIQUE /* 角色名称 */,
    "desc" VARCHAR(500)   /* 角色描述 */
) /* 角色模型，用于存储系统角色信息。 */;
CREATE INDEX IF NOT EXISTS "idx_role_created_7f5f71" ON "role" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_role_updated_5dd337" ON "role" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_role_name_e5618b" ON "role" ("name");
CREATE TABLE IF NOT EXISTS "test_cases" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "test_case_id" INT NOT NULL  /* 测试用例的唯一标识。 */,
    "title" VARCHAR(200) NOT NULL  /* 测试用例的标题。 */,
    "desc" TEXT   /* 测试用例的详细描述。 */,
    "priority" VARCHAR(1) NOT NULL  /* 测试用例的优先级。 */,
    "status" VARCHAR(3) NOT NULL  DEFAULT '未开始' /* 测试用例的当前状态。 */,
    "preconditions" TEXT   /* 测试用例的前置条件。 */,
    "postconditions" TEXT   /* 测试用例的后置条件。 */,
    "tags" VARCHAR(4) NOT NULL  DEFAULT '功能测试' /* 测试用例的标签列表，用于分类或过滤。 */,
    "requirement_id" INT NOT NULL  /* 测试用例的相关需求。 */,
    "project_id" INT NOT NULL  /* 测试用例的相关项目。 */,
    "creator" VARCHAR(100) NOT NULL  /* 测试用例的创建者姓名。 */
) /* 测试用例模型 */;
CREATE INDEX IF NOT EXISTS "idx_test_cases_created_c2f56b" ON "test_cases" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_test_cases_updated_44d4c2" ON "test_cases" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_test_cases_test_ca_74d8a1" ON "test_cases" ("test_case_id");
CREATE INDEX IF NOT EXISTS "idx_test_cases_require_42e995" ON "test_cases" ("requirement_id");
CREATE INDEX IF NOT EXISTS "idx_test_cases_project_5c9a88" ON "test_cases" ("project_id");
CREATE TABLE IF NOT EXISTS "test_steps" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "step_id" INT NOT NULL  /* 测试步骤的唯一标识。 */,
    "test_case_id" INT NOT NULL  /* 关联的测试用例ID。 */,
    "description" TEXT NOT NULL  /* 测试步骤的描述。 */,
    "expected_result" TEXT NOT NULL  /* 测试步骤的预期结果。 */
) /* 测试用例步骤模型 */;
CREATE INDEX IF NOT EXISTS "idx_test_steps_created_826bad" ON "test_steps" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_test_steps_updated_634f53" ON "test_steps" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_test_steps_step_id_c3105a" ON "test_steps" ("step_id");
CREATE INDEX IF NOT EXISTS "idx_test_steps_test_ca_0464a3" ON "test_steps" ("test_case_id");
CREATE TABLE IF NOT EXISTS "user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "username" VARCHAR(20) NOT NULL UNIQUE /* 用户名称 */,
    "alias" VARCHAR(30)   /* 姓名 */,
    "email" VARCHAR(255) NOT NULL UNIQUE /* 邮箱 */,
    "phone" VARCHAR(20)   /* 电话 */,
    "password" VARCHAR(128)   /* 密码 */,
    "is_active" INT NOT NULL  DEFAULT 1 /* 是否激活 */,
    "is_superuser" INT NOT NULL  DEFAULT 0 /* 是否为超级管理员 */,
    "last_login" TIMESTAMP   /* 最后登录时间 */,
    "dept_id" INT   /* 部门ID */
) /* 用户模型，用于存储系统用户信息。 */;
CREATE INDEX IF NOT EXISTS "idx_user_created_b19d59" ON "user" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_user_updated_dfdb43" ON "user" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_user_usernam_9987ab" ON "user" ("username");
CREATE INDEX IF NOT EXISTS "idx_user_alias_6f9868" ON "user" ("alias");
CREATE INDEX IF NOT EXISTS "idx_user_email_1b4f1c" ON "user" ("email");
CREATE INDEX IF NOT EXISTS "idx_user_phone_4e3ecc" ON "user" ("phone");
CREATE INDEX IF NOT EXISTS "idx_user_is_acti_83722a" ON "user" ("is_active");
CREATE INDEX IF NOT EXISTS "idx_user_is_supe_b8a218" ON "user" ("is_superuser");
CREATE INDEX IF NOT EXISTS "idx_user_last_lo_af118a" ON "user" ("last_login");
CREATE INDEX IF NOT EXISTS "idx_user_dept_id_d4490b" ON "user" ("dept_id");
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS "role_api" (
    "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE,
    "api_id" BIGINT NOT NULL REFERENCES "api" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "role_menu" (
    "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE,
    "menu_id" BIGINT NOT NULL REFERENCES "menu" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "test_cases_test_steps" (
    "test_cases_id" BIGINT NOT NULL REFERENCES "test_cases" ("id") ON DELETE CASCADE,
    "teststep_id" BIGINT NOT NULL REFERENCES "test_steps" ("id") ON DELETE CASCADE
) /* 测试步骤列表。 */;
CREATE TABLE IF NOT EXISTS "user_role" (
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
