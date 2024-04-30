import mysql.connector
from mysql.connector import pooling
import logging

# Set up logging
logging.basicConfig(filename='chatbot_debug.log', level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')

class DatabaseManager:
    def __init__(self, db_config):
        # Initialize the DatabaseManager with a connection pool.
        self.pool = pooling.MySQLConnectionPool(**db_config)

    def get_connection(self):
        # Get database connection from the connection pool.
        try:
            return self.pool.get_connection()
        except mysql.connector.Error as err:
            print(f"Error connecting to MySQL: {err}")
            return None

    def fetch_user_messages(self, username, session_id):
        # Fetch all messages for a given user and session.
        query = """
        SELECT message, response, timestamp 
        FROM Chats 
        WHERE username = %s AND session_id = %s 
        ORDER BY timestamp ASC
        """
        return self._execute_query(query, (username, session_id))

    def fetch_sessions(self, username):
        # Fetch all sessions for a given user.
        query = "SELECT session_id, session_name FROM Sessions WHERE username = %s"
        return self._execute_query(query, (username,))

    def create_new_session(self, username, session_name):
        query = "INSERT INTO Sessions (username, session_name) VALUES (%s, %s)"
        return self._execute_query(query, (username, session_name), commit=True)

    def delete_session(self, session_id):
        # Delete a session based on session ID.
        query = "DELETE FROM Sessions WHERE session_id = %s"
        return self._execute_query(query, (session_id,), commit=True)

    def get_course_details(self, course_id):
        return self._execute_query("SELECT course_name, course_description FROM Courses WHERE course_id = %s", (course_id,))

    def get_module_details(self, course_id):
        return self._execute_query("SELECT module_name, module_description FROM Modules WHERE course_id = %s", (course_id,))

    def get_lecture_details(self, module_id):
        return self._execute_query("SELECT lecture_date FROM Lectures WHERE module_id = %s", (module_id,))


    def _execute_query(self, query, params, fetch=True, commit=False):
        with self.get_connection() as conn:
            if conn is None:
                return None if fetch else False
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    if commit:
                        conn.commit()
                    return cursor.fetchall() if fetch else True
            except mysql.connector.Error as err:
                print(f"SQL Error: {err}")
                if commit:
                    conn.rollback()
                return None if fetch else False

    def get_response_from_db(self, intent_id):
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            query = "SELECT response_text FROM Responses WHERE intent_id = %s"
            cursor.execute(query, (intent_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return "No response found."
        except Exception as e:
            print(f"Error retrieving response: {e}")
            return "Sorry, I encountered an error while processing your request."
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
