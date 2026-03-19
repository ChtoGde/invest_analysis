import psycopg2
from psycopg2 import OperationalError


class CONNECTION_DB():
    def __init__(self, db_name, db_user, db_password, db_host='localhost', db_port=5432):
        try:
            self.conn = psycopg2.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port)
            self.conn.autocommit = False
            print('Подключение к БД установлено')
        except OperationalError as e:
            print(f'Ошибка: {e}')
            self.conn = None


    def execute(self, query: str):
        if not self.conn:
            print('Нет подключения к БД')
            return

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
            self.conn.commit()
        except OperationalError as e:
            self.conn.rollback()
            print(f'Ошибка: {e}')
            raise


    def insert_into(self, table: str, columns: str, values):
        query = f"""INSERT INTO {table} {columns}
                VALUES {values}"""
        self.execute(query)


    def clear_table(self, table: str):
        query = f"""DELETE FROM {table}"""
        self.execute(query)


    def update_table(self, table: str, column: str, value, where: dict):
        query = f"""UPDATE {table}
                SET {column} = {value}
                WHERE {list(where.keys())[0]} = '{list(where.values())[0]}'"""
        self.execute(query)


    def delete_from(self, table: str, where: dict):
        query = f"""DELETE FROM {table}
                WHERE {list(where.keys())[0]} = '{list(where.values())[0]}'"""
        self.execute(query)


    def close(self):
        if self.conn:
            self.conn.close()
