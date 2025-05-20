from tortoise.expressions import Q  # Tortoise ORM 的查询条件构造工具
from tortoise.transactions import atomic  # 数据库事务装饰器

from app.core.crud import CRUDBase  # CRUD 基类，提供通用的增删改查方法
from app.models.admin import Dept, DeptClosure  # 定义部门模型和部门闭包表模型的 Tortoise ORM 类
from app.schemas.depts import DeptCreate, DeptUpdate  # 定义部门创建和更新的 Pydantic 模型


class DeptController(CRUDBase[Dept, DeptCreate, DeptUpdate]):
    """
    部门控制器类，用于管理部门数据。
    """
    def __init__(self):
        super().__init__(model=Dept)  # 初始化父类，指定模型为 Dept

    async def get_dept_tree(self, name: str = ""):
        """
        获取部门树结构。
        参数:
            name (str): 部门名称（可选），用于过滤部门
        返回:
            list: 部门树结构的列表
        """
        q = Q()  # 初始化查询条件
        # 获取所有未被软删除的部门
        q &= Q(is_deleted=False)
        if name:  # 如果提供了部门名称，则按名称模糊匹配
            q &= Q(name__contains=name)
        all_depts = await self.model.filter(q).order_by("order")  # 查询所有符合条件的部门并按顺序排序

        # 辅助函数，用于递归构建部门树
        def build_tree(parent_id: int):
            return [
                {
                    "id": dept.id,  # 部门 ID
                    "name": dept.name,  # 部门名称
                    "desc": dept.desc,  # 部门描述
                    "order": dept.order,  # 部门顺序
                    "parent_id": dept.parent_id,  # 父部门 ID
                    "children": build_tree(dept.id),  # 递归构建子部门
                }
                for dept in all_depts
                if dept.parent_id == parent_id  # 只处理当前层级的部门
            ]

        # 从顶级部门（parent_id=0）开始构建部门树
        dept_tree = build_tree(0)
        return dept_tree

    async def get_dept_info(self):
        """
        获取部门信息（未实现）。
        """
        pass

    async def update_dept_closure(self, obj: Dept):
        """
        更新部门闭包表。
        参数:
            obj (Dept): 部门对象
        """
        parent_depts = await DeptClosure.filter(descendant=obj.parent_id)  # 查询父部门的所有闭包关系
        dept_closure_objs: list[DeptClosure] = []  # 存储新的闭包关系对象
        # 插入父级关系
        for item in parent_depts:
            print(item.ancestor, item.descendant)  # 打印祖先和后代关系（调试用）
            dept_closure_objs.append(
                DeptClosure(ancestor=item.ancestor, descendant=obj.id, level=item.level + 1)
            )  # 创建新的闭包关系
        # 插入自身关系
        dept_closure_objs.append(DeptClosure(ancestor=obj.id, descendant=obj.id, level=0))
        # 批量创建闭包关系
        await DeptClosure.bulk_create(dept_closure_objs)

    @atomic()  # 使用事务确保操作的原子性
    async def create_dept(self, obj_in: DeptCreate):
        """
        创建新部门。
        参数:
            obj_in (DeptCreate): 部门创建模型
        """
        if obj_in.parent_id != 0:  # 如果不是顶级部门，则检查父部门是否存在
            await self.get(id=obj_in.parent_id)
        new_obj = await self.create(obj_in=obj_in)  # 创建新部门
        await self.update_dept_closure(new_obj)  # 更新闭包表

    @atomic()  # 使用事务确保操作的原子性
    async def update_dept(self, obj_in: DeptUpdate):
        """
        更新部门信息。
        参数:
            obj_in (DeptUpdate): 部门更新模型
        """
        dept_obj = await self.get(id=obj_in.id)  # 获取要更新的部门对象
        # 如果修改了父部门，则需要重新计算闭包关系
        if dept_obj.parent_id != obj_in.parent_id:
            await DeptClosure.filter(ancestor=dept_obj.id).delete()  # 删除旧的祖先关系
            await DeptClosure.filter(descendant=dept_obj.id).delete()  # 删除旧的后代关系
            await self.update_dept_closure(dept_obj)  # 更新闭包表
        # 更新部门信息
        dept_obj.update_from_dict(obj_in.model_dump(exclude_unset=True))  # 更新字段
        await dept_obj.save()  # 保存更新

    @atomic()  # 使用事务确保操作的原子性
    async def delete_dept(self, dept_id: int):
        """
        删除部门。
        参数:
            dept_id (int): 部门 ID
        """
        obj = await self.get(id=dept_id)  # 获取要删除的部门对象
        obj.is_deleted = True  # 标记为已删除（软删除）
        await obj.save()  # 保存更新
        # 删除闭包表中的相关记录
        await DeptClosure.filter(descendant=dept_id).delete()


# 实例化部门控制器
dept_controller = DeptController()