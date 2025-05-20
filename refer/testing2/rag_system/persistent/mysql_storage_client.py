# pip install aiomysql
import pymysql
from aiomysql import connection
from chainlit.data.storage_clients.base import BaseStorageClient
from chainlit.logger import logger


class MySqlStorageClient(BaseStorageClient):
    """
    Class to enable storage in a MYSQL database.

    parms:
        host: Hostname or IP address of the MYSQL server.
        dbname: Name of the database to connect to.
        user: User name used to authenticate.
        password: Password used to authenticate.
        port: Port number to connect to (default: 3306).
    """

    def __init__(self, host: str, dbname: str, user: str, password: str, port: int = 5432):
        try:
            self.conn: connection = pymysql.Connect(
                host=host,
                port=port,
                user=user,
                passwd=password,
                db=dbname,
                charset='utf8'
            )
            logger.info("MysqlStorageClient initialized")
        except Exception as e:
            logger.warn(f"MysqlStorageClient initialization error: {e}")

