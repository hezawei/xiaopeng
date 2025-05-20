from dotenv import load_dotenv
from dquestion.dquestion import DQuestionChat

load_dotenv()
dq = DQuestionChat()
dq.connect_to_sqlite('Chinook.sqlite')
df_ddl = dq.run_sql("SELECT type, sql FROM sqlite_master WHERE sql is not null")
# dq.connect_to_mysql(host="localhost", dbname="huice_test", user="root", password="mysql", port=3306)
# df_ddl = dq.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS where table_schema = 'huice_test'")
# plan = dq.get_training_plan_generic(df_ddl)
# dq.train(plan=plan)
for ddl in df_ddl['sql'].to_list():
    dq.train(ddl=ddl)

