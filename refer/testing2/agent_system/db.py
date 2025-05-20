import pymysql
from pymysql import Error

def create_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='mysql',
        database="ai_db",
        charset='utf8mb4',
        # cursorclass=pymysql.cursors.DictCursor
    )


class BusinessRequirementCRUD:
    @staticmethod
    def create(requirement):
        sql = """
        INSERT INTO business_requirement (
            requirement_id, requirement_name, requirement_type, parent_requirement,
            module, requirement_level, reviewer, estimated_hours, description, acceptance_criteria
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with create_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        requirement['requirement_id'],
                        requirement['requirement_name'],
                        requirement['requirement_type'],
                        requirement.get('parent_requirement'),
                        requirement['module'],
                        requirement['requirement_level'],
                        requirement['reviewer'],
                        requirement['estimated_hours'],
                        requirement['description'],
                        requirement['acceptance_criteria']
                    ))
                    conn.commit()
                    return True
        except Error as e:
            print(f"Error creating requirement: {e}")
            return False

    @staticmethod
    def get_by_id(requirement_id):
        sql = "SELECT * FROM business_requirement WHERE requirement_id = %s"
        try:
            with create_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (requirement_id,))
                    return cursor.fetchone()
        except Error as e:
            print(f"Error fetching requirement: {e}")
            return None

    @staticmethod
    def update(requirement_id, update_data):
        fields = []
        values = []
        for key, value in update_data.items():
            fields.append(f"{key} = %s")
            values.append(value)
        values.append(requirement_id)

        sql = f"UPDATE business_requirement SET {', '.join(fields)} WHERE requirement_id = %s"
        try:
            with create_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, values)
                    conn.commit()
                    return True
        except Error as e:
            print(f"Error updating requirement: {e}")
            return False

    @staticmethod
    def delete(requirement_id):
        sql = "DELETE FROM business_requirement WHERE requirement_id = %s"
        try:
            with create_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (requirement_id,))
                    conn.commit()
                    return True
        except Error as e:
            print(f"Error deleting requirement: {e}")
            return False

    @staticmethod
    def get_all():
        sql = "SELECT * FROM business_requirement"
        try:
            with create_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    return cursor.fetchall()
        except Error as e:
            print(f"Error fetching all requirements: {e}")
            return []


if __name__ == "__main__":
    # 插入数据
    new_req = {
        "requirement_id": "REQ001",
        "requirement_name": "用户登录功能",
        "requirement_type": "功能需求",
        "parent_requirement": None,
        "module": "认证模块",
        "requirement_level": "核心功能",
        "reviewer": "张三",
        "estimated_hours": 8,
        "description": "实现用户通过账号密码登录",
        "acceptance_criteria": "成功跳转至主页"
    }
    BusinessRequirementCRUD.create(new_req)

    # 查询数据
    req = BusinessRequirementCRUD.get_by_id("REQ001")
    print(req)

    # 更新数据
    update_data = {"estimated_hours": 10, "reviewer": "李四"}
    BusinessRequirementCRUD.update("REQ001", update_data)

    # 删除数据
    BusinessRequirementCRUD.delete("REQ001")

