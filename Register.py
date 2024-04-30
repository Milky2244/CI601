import tkinter as tk
import mysql.connector
from mysql.connector import pooling
import bcrypt

# Global configuration for database access
db_config = {
    'host': '165.227.235.122',
    'user': 'bm676_chatbotAdmin',
    'password': 'University123@',
    'database': 'bm676_chatbot',
    'port': '3306',
    'pool_name': 'mypool',
    'pool_size': 5
}

# Create a connection pool
cnx_pool = pooling.MySQLConnectionPool(**db_config)

def get_database_connection():
    try:
        return cnx_pool.get_connection()
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def register_user(username, password):
    connection = get_database_connection()
    if not connection:
        print("Connection to database failed")
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT username FROM Users WHERE username = %s", (username,))
        if cursor.fetchone():
            return "Username already exists"
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Insert new user
        cursor.execute("INSERT INTO Users (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
        connection.commit()
        return "Registration successful"
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return "Failed to register"
    finally:
        if connection:
            connection.close()

class RegistrationApp:
    def __init__(self, master):
        self.master = master
        master.title("Register New User")

        tk.Label(master, text="Username:").pack()
        self.username_entry = tk.Entry(master)
        self.username_entry.pack()

        tk.Label(master, text="Password:").pack()
        self.password_entry = tk.Entry(master, show="*")
        self.password_entry.pack()

        self.register_button = tk.Button(master, text="Register", command=self.register)
        self.register_button.pack()

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        result = register_user(username, password)
        tk.Label(self.master, text=result).pack()

if __name__ == '__main__':
    root = tk.Tk()
    app = RegistrationApp(root)
    root.mainloop()
