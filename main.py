# Importing necessary libraries and modules
import tkinter as tk
import logging
import re
import mysql.connector
import bcrypt
import threading
from mysql.connector import pooling
from tkinter import Text, Scrollbar, Entry, Button, Toplevel, simpledialog, messagebox, Menu
from database_manager import DatabaseManager

import nltk
from nltk import word_tokenize, ne_chunk, pos_tag
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.corpus import wordnet

# Global configuration for database access
db_config = {
    'host': '165.227.235.122',
    'user': 'bm676_chatbotAdmin',
    'password': 'University123@',
    'database': 'bm676_chatbot',
    'port': '3306',
    'pool_name': 'mypool',
    'pool_size': 32
}

cnx_pool = pooling.MySQLConnectionPool(**db_config)

# Preprocesses text for NLP tasks
def preprocess_text(text):
    tokens = word_tokenize(text.lower())
    pos_tags = pos_tag(tokens)
    lemmatizer = WordNetLemmatizer()
    lemmas = [lemmatizer.lemmatize(token, get_wordnet_pos(tag)) for token, tag in pos_tags]
    return ' '.join(lemmas)

# Converts treebank POS tags to WordNet POS tags
def get_wordnet_pos(treebank_tag):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN  # Default to noun

# Gets a connection from the database connection pool
def get_database_connection():
    try:
        return cnx_pool.get_connection()
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None  # Explicitly returning None to indicate failure

# Retrieves a response from the database based on intent
def get_response_from_db(self, intent):
    try:
        connection = get_database_connection()  # Assume a method that sets up the DB connection
        cursor = connection.cursor()
        query = "SELECT response_text FROM Responses WHERE intent_id = %s"
        cursor.execute(query, (intent,))
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

# Fetches past messages for a specific session of a user from the database
def fetch_user_messages(username, session_id):
    connection = get_database_connection()
    if connection is None:
        print("Failed to connect to the database.")
        return []
    try:
        cursor = connection.cursor()
        # Query to fetch messages for a specific session
        cursor.execute("""SELECT message, response, timestamp FROM Chats WHERE username = %s AND session_id = %s ORDER BY timestamp ASC """, (username, session_id))
        messages = cursor.fetchall()
        cursor.close()
        return messages
    except mysql.connector.Error as err:
        print(f"Database query error: {err}")
        return []
    finally:
        if connection:
            connection.close()

# Fetches past messages for a specific session of a user from the database, ordered by timestamp.
def fetch_session_messages(username, session_id):
    connection = get_database_connection()
    if not connection:
        return []
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT message, response, timestamp FROM Chats WHERE username = %s AND session_id = %s ORDER BY timestamp ASC""", (username, session_id))
        messages = cursor.fetchall()
        cursor.close()
        return messages
    except mysql.connector.Error as err:
        print(f"Database query error: {err}")
        return []
    finally:
        if connection:
            connection.close()

# Creates a new chat session
def create_new_session(username, session_name):
    """Create a new chat session."""
    connection = get_database_connection()
    if not connection:
        return "Database connection error."
    try:
        cursor = connection.cursor()
        cursor.execute("INSERT INTO Sessions (username, session_name) VALUES (%s, %s)", (username, session_name))
        connection.commit()
        return "Session created successfully."
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


class ChatbotApp:
    def __init__(self, master):

        # Initialize the main application window        
        self.master = master
        self.master.withdraw()  # Ensure main window is hidden initially
        self.master.title("University Chatbot")

        # Initialize variables for managing chat sessions    
        self.sessions_list = None
        self.debug_mode = False 
        self.current_session = None
        self.user_id = None
        self.course_id = None
        self.session_map = {}

        # Define color schemes for light and dark modes
        self.is_dark_mode = False  # Track whether dark mode is enabled
        self.colors = {
            "light": {"bg": "#FFFFFF", "text": "#000000", "button": "#E0E0E0", "input_bg": "#FFFFFF", "input_fg": "#000000"},
            "dark": {"bg": "#333333", "text": "#FFFFFF", "button": "#555555", "input_bg": "#424242", "input_fg": "#FFFFFF"}
        }
        self.current_colors = self.colors["light"]  # Start with light mode
        self.create_menu_bar() # Initialize the menu bar
        self.db_manager = DatabaseManager(db_config) # Initialize the database manager
        self.preload_nltk_resources() # Preload necessary NLTK resources
        self.login_window() # Open the login window

    def preload_nltk_resources(self):
        # Load NLTK resources
        print("Loading NLTK resources...")
        nltk.download('maxent_ne_chunker')
        nltk.download('words')
        nltk.download('punkt')
        nltk.download('wordnet')
        nltk.download('averaged_perceptron_tagger')
        nltk.download('punkt')
        print("NLTK resources loaded successfully.")

    def toggle_dark_mode(self):
        # Toggle between dark and light modes
        self.is_dark_mode = not self.is_dark_mode
        self.current_colors = self.colors["dark"] if self.is_dark_mode else self.colors["light"]
        self.update_ui_colors()

    def update_ui_colors(self):
        # Update master window background
        self.master.config(bg=self.current_colors["bg"])

        # Update widgets recursively
        def update_widget_colors(widget):
            widget_class = widget.winfo_class()
            if widget_class in ("Frame", "Toplevel"):
                widget.config(bg=self.current_colors["bg"])
            if widget_class == "Text":
                widget.config(bg=self.current_colors["input_bg"], fg=self.current_colors["input_fg"])
            elif widget_class == "Button":
                widget.config(bg=self.current_colors["button"], fg=self.current_colors["text"])
            elif widget_class == "Entry":
                widget.config(bg=self.current_colors["input_bg"], fg=self.current_colors["input_fg"])
            elif widget_class == "Listbox":
                widget.config(bg=self.current_colors["input_bg"], fg=self.current_colors["input_fg"])
            # Recurse into children of this widget
            for child in widget.winfo_children():
                update_widget_colors(child)
        update_widget_colors(self.master)

    def create_menu_bar(self):
        # Create the menu bar with settings options
        self.menu_bar = Menu(self.master)
        self.master.config(menu=self.menu_bar)
        settings_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Toggle Dark Mode", command=self.toggle_dark_mode)
        settings_menu.add_command(label="Debug Mode", command=self.toggle_debug_mode)
        settings_menu.add_separator()
        settings_menu.add_command(label="Logout", command=self.logout)

    def setup_chat_widgets(self):
        # Clear existing frames but keep the menu intact
        for widget in self.master.winfo_children():
            if not isinstance(widget, Menu):
                widget.destroy()

        # Ensure the menu is correctly set up
        self.create_menu_bar()

        # Main chat area frame
        chat_frame = tk.Frame(self.master)
        chat_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Left frame for sessions and buttons
        left_frame = tk.Frame(self.master)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Sessions list
        self.sessions_list = tk.Listbox(left_frame, height=20, width=30)
        self.sessions_list.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.sessions_list.bind('<<ListboxSelect>>', self.on_session_select)

        # Button frame for session management
        button_frame = tk.Frame(left_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        plus_button = tk.Button(button_frame, text="+", command=self.create_session)
        plus_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.delete_button = tk.Button(button_frame, text="Delete", command=self.delete_session, state=tk.DISABLED)
        self.delete_button.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # Text area for displaying messages
        self.text_area = tk.Text(chat_frame, wrap=tk.WORD, height=20, width=50, bg='light cyan', fg='black')
        self.scroll_bar = tk.Scrollbar(chat_frame, command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=self.scroll_bar.set)
        self.scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Frame for user input
        input_frame = tk.Frame(chat_frame)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        self.user_input = tk.Entry(input_frame, width=40)
        self.user_input.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.user_input.bind("<Return>", self.process_user_input)
        self.send_button = tk.Button(input_frame, text="Send", command=self.process_user_input)
        self.send_button.pack(side=tk.RIGHT)

    def initial_greeting(self):
        self.display_message("Chatbot: Welcome to the University Chatbot! How can I assist you today?")

    def logout(self):
        # Log out the current user
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self.clear_sessions()  # Clear session data
            self.master.withdraw()  # Hide the main window
            self.login_window()  # Reopen the login window for new login

    def clear_sessions(self):
        # Additional cleanup logic
        self.sessions_list.delete(0, tk.END)  # Clear the session list
        self.text_area.delete('1.0', tk.END)  # Clear the chat area
        self.current_session = None
        self.session_map.clear()
        self.user_input.delete(0, tk.END)  # Clear any text input

    def toggle_debug_mode(self):
        # Toggle debug mode
        self.debug_mode = not self.debug_mode
        print("Debug Mode:", "Enabled" if self.debug_mode else "Disabled")

    def toggle_dark_mode(self):
        # Toggle dark mode
        self.is_dark_mode = not self.is_dark_mode
        self.current_colors = self.colors["dark"] if self.is_dark_mode else self.colors["light"]
        self.update_ui_colors()

    def delete_session(self):
        # Delete the selected chat session
        response = messagebox.askquestion("Delete Session", "Are you sure you want to delete this chat?")
        if response == 'yes':
            if self.remove_session_from_db(self.current_session):
                messagebox.showinfo("Delete Session", "Session deleted successfully.")
                self.refresh_sessions_list()
                self.current_session = None
            else:
                messagebox.showerror("Delete Session", "Failed to delete session.")

    def fetch_intent_patterns(self):
            """Fetch intent patterns from the database."""
            connection = get_database_connection()
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT intent_id, regex_pattern FROM IntentPatterns")
                patterns = {row[0]: re.compile(row[1]) for row in cursor.fetchall()}
                return patterns
            finally:
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()

    def fetch_sessions(self):
        try:
            sessions = self.db_manager.fetch_sessions(self.username)  # Using the method from the DatabaseManager
            return sessions
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to fetch sessions: {str(e)}")
            return []
        
    def remove_session_from_db(self, session_id):
        """Remove a session from the database."""
        connection = get_database_connection()
        if not connection:
            return False
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM Sessions WHERE session_id = %s", (session_id,))
            connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"Error deleting session: {err}")
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def fetch_course_details(self, course_id):
        query = "SELECT course_name, course_description FROM Courses WHERE course_id = %s"
        return self._execute_query(query, (course_id,))

    def fetch_module_details(self, course_id):
        query = "SELECT module_name, module_description FROM Modules WHERE course_id = %s"
        return self._execute_query(query, (course_id,))

    def fetch_lecture_schedule(self, module_id):
        query = "SELECT lecture_date FROM Lectures WHERE module_id = %s"
        return self._execute_query(query, (module_id,))


    def generate_response(self, intents):
        responses = []
        for intent in intents:
            if intent == 'course_details':
                course_info = self.db_manager.get_course_details(self.course_id)
                if course_info:
                    formatted_course_info = 'Here is some information about your current course! '
                    for (name, description) in course_info:
                        formatted_course_info += f"{name} - {description}. "
                    formatted_course_info = formatted_course_info.rstrip('. ')
                    responses.append(formatted_course_info)

            elif intent == 'module_details':
                module_info = self.db_manager.get_module_details(self.course_id)
                if module_info:
                    formatted_module_info = 'Module Info: '
                    for (name, description) in module_info:
                        formatted_module_info += f"{name} - {description}. "
                    formatted_module_info = formatted_module_info.rstrip('. ')
                    responses.append(formatted_module_info)

            elif intent == 'lecture_details':
                lecture_info = self.db_manager.get_lecture_details(self.course_id)
                if lecture_info:
                    formatted_lecture_info = 'Lecture Schedule: '
                    for (lecture_date,) in lecture_info:
                        formatted_lecture_info += f"{lecture_date.strftime('%Y-%m-%d %H:%M')}, "
                    formatted_lecture_info = formatted_lecture_info.rstrip(', ')
                    responses.append(formatted_lecture_info)

            else:
                response = self.db_manager.get_response_from_db(intent)
                responses.append(response if response else "No response found.")

        return ' '.join(responses) if responses else "Sorry, I couldn't understand that."

    @staticmethod
    def get_synonyms(word):
        """Fetch synonyms for a word from the NLTK WordNet corpus."""
        synonyms = set()
        for synset in nltk.corpus.wordnet.synsets(word):
            for lemma in synset.lemmas():
                synonyms.add(lemma.name().replace('_', ' '))
        return synonyms
    
    def predict_intents(self, query):
        tokens = nltk.word_tokenize(query.lower())
        pos_tags = nltk.pos_tag(tokens)

        # Extract verbs, nouns and adjectives and expand them with synonyms
        verbs = set()
        nouns = set()
        adjectives = set() 

        for word, tag in pos_tags:
            synonyms = self.get_synonyms(word)
            if 'VB' in tag:
                verbs.update(synonyms)
            elif 'NN' in tag:
                nouns.update(synonyms)
            elif 'JJ' in tag:  
                adjectives.update(synonyms)

        # Print debugging information if debug mode is enabled
        if self.debug_mode:
            print("Tokens and POS Tags:", list(zip(tokens, pos_tags)))
            print("Verbs with Synonyms:", verbs)
            print("Nouns with Synonyms:", nouns)

        # Considering 'library' could be tagged as JJ
        relevant_nouns = nouns.union(adjectives)  # Combine nouns and adjectives for checking

        detected_intents = set()

        if any(verb in {'register', 'enroll', 'sign up'} for verb in verbs):
            detected_intents.add('4')  # Intent ID for enrollment

        # Checking for course-related queries
        if any(noun in {'course','degree','qualification'} for noun in relevant_nouns):
            detected_intents.add('course_details')  # Custom intent for course details

        if any(noun in {'module','unit'} for noun in relevant_nouns):
            detected_intents.add('module_details')  # Custom intent for module details

        if any(noun in {'lecture','seminar','study group','lesson','tutorial','workshop'} for noun in relevant_nouns):
            detected_intents.add('lecture_details')  # Custom intent for lecture schedules

        if 'library' in relevant_nouns:
            if any(term in {'hours', 'time', 'schedule'} for term in relevant_nouns):
                detected_intents.add('2')  # For library hours
            elif any(term in {'location', 'where', 'find'} for term in relevant_nouns):
                detected_intents.add('library_location_id')  # New intent for library location
            else:
                detected_intents.add('library_general')
        if any(noun in {'event', 'happening', 'occasion'} for noun in relevant_nouns):
            detected_intents.add('5')  # Intent ID for events
        if any(noun in {'contact', 'support', 'help'} for noun in relevant_nouns):
            detected_intents.add('6')  # Intent ID for contact information
        if any(noun in {'goodbye', 'bye', 'farewell'} for noun in relevant_nouns):
            detected_intents.add('7')  # Intent ID for farewells

        # Fetching regex patterns from the database
        patterns = self.fetch_intent_patterns()
        for intent_id, pattern in patterns.items():
            if pattern.search(query):
                detected_intents.add(str(intent_id))
                
        return sorted(detected_intents) if detected_intents else ['default_fallback_intent']

    def merge_responses(intents):
        responses = []
        for intent in intents:
            response = get_response_from_db(intent)  # Assuming this function fetches the appropriate response for an intent
            if response:
                responses.append(response)

        # Combine responses. This could be as simple as joining them with a space or designing a more complex aggregation logic.
        return " ".join(responses)
    
    def process_user_input(self, event=None):
        if not self.current_session:
            messagebox.showwarning("No Session Selected", "Please select a session before sending a message.")
            return
        
        user_query = self.user_input.get()
        self.user_input.delete(0, tk.END)
        self.display_message("You: " + user_query, 'blue')  # Display user input immediately
        
        # Start a new thread to handle input processing and response generation
        threading.Thread(target=self.handle_input, args=(user_query,)).start()

    def handle_input(self, user_query):
        """Handles the processing of user input in a separate thread."""

        # Debug input if debug mode is enabled
        if self.debug_mode:
            print("Processing Input:", user_query)

        lemmatized_query = preprocess_text(user_query)  # No need to unpack, as preprocess_text() returns only the lemmatized text

        # Perform intent prediction
        intents = self.predict_intents(lemmatized_query)
        # Generate response based on intents
        response = self.generate_response(intents)

        if self.debug_mode:
            print("Detected Intents:", intents)
            print("Generated Response:", response)

        # Display response
        self.display_message("Chatbot: " + response, 'purple')
        # Save the user input and chatbot response to the database
        self.save_chat(self.username, user_query, response, self.current_session)

    def display_message(self, message, color='black'):
        """Thread-safe message display in the text area."""
        def do_display():
            self.text_area.tag_configure(color, foreground=color)
            self.text_area.insert(tk.END, message + "\n", color)  # Add a newline character without extra spacing
            self.text_area.see(tk.END)
        self.text_area.after(0, do_display)

    def save_chat(self, username, message, response, session_id):
        """Save chat to the database with session_id."""
        connection = get_database_connection()
        if connection is None:
            print("Failed to connect to the database for saving the chat.")
            return
        try:
            cursor = connection.cursor()

            # Preprocess message using NLTK
            processed_message = preprocess_text(message)

            # Insert the original and processed messages into the database
            sql = "INSERT INTO Chats (username, message, processed_message, response, session_id) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (username, message, processed_message, response, session_id))
            connection.commit()
            print("Chat saved successfully.")
        except mysql.connector.Error as err:
            print(f"Failed to save chat: {err}")
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def clear_sessions(self):
        # Clearing the user data and any session data
        self.username = None
        self.course_id = None
        self.current_session = None
        self.session_map.clear()
        self.sessions_list.delete(0, tk.END)  # Clear the session list in the UI
        self.text_area.delete('1.0', tk.END)  # Clear the chat history

    def load_and_display_messages(self, session_id):
        # Use the database manager to fetch messages
        messages = self.db_manager.fetch_user_messages(self.username, session_id)
        self.text_area.delete('1.0', tk.END)  # Clear the text area

        if messages:
            for message, response, timestamp in messages:
                formatted_user_msg = f"{timestamp}: You: {message}"
                formatted_bot_msg = f"Chatbot: {response}\n\n"
                self.display_message(formatted_user_msg, 'blue')
                self.display_message(formatted_bot_msg, 'purple')
            self.display_message("---- Starting new dialogue ----\n", 'green')
        else:
            self.display_message("No previous messages found. Starting new dialogue.\n", 'green')

    def on_session_select(self, event):
        """Handle session selection from the list."""
        selection = self.sessions_list.curselection()
        if selection:
            index = selection[0]
            session_id = self.session_map[index]  # Retrieve the session ID using the index
            self.current_session = session_id
            self.load_and_display_messages(session_id)
            self.delete_button['state'] = tk.NORMAL  # Enable delete button
            self.enable_chat(True)  # Enable chat when a session is selected
        else:
            self.current_session = None
            self.delete_button['state'] = tk.DISABLED  # Disable delete button if no session is selected
            self.enable_chat(False)  # Disable chat when no session is selected

    def enable_chat(self, enable):
        """Enable or disable chat input and send button."""
        state = tk.NORMAL if enable else tk.DISABLED
        self.user_input['state'] = state
        self.send_button['state'] = state
        
    def create_session(self):
        if len(self.session_map) >= 5:
            messagebox.showerror("Session Limit", "Maximum of 5 sessions are allowed.")
            return

        session_name = simpledialog.askstring("New Session", "Enter session name:")
        if session_name:
            success = self.db_manager.create_new_session(self.username, session_name)
            self.refresh_sessions_list()  # Always refresh the list regardless of success
                
    def refresh_sessions_list(self):
        try:
            sessions = self.db_manager.fetch_sessions(self.username)
            if sessions is None:
                sessions = []  # Safeguard against NoneType

            self.sessions_list.delete(0, tk.END)  # Ensure sessions_list is initialized
            self.session_map.clear()

            for index, (session_id, session_name) in enumerate(sessions):
                listbox_entry = f"{session_name} ({session_id})"
                self.sessions_list.insert(tk.END, listbox_entry)
                self.session_map[index] = session_id

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            # Add debugging print or logging here to find out more details about the exception
            print(f"Exception during session list refresh: {e}")

    def login_window(self):
        # Destroy previous login window if it exists
        if hasattr(self, 'login'):
            self.login.destroy()

        self.login = Toplevel(self.master)
        self.login.title("Login")
        self.login.geometry("300x150")  # Adjusted size for better fit

        # Positioning the window in the center of the screen
        ws = self.login.winfo_screenwidth()
        hs = self.login.winfo_screenheight()
        x = (ws / 2) - (300 / 2)
        y = (hs / 2) - (150 / 2)
        self.login.geometry('%dx%d+%d+%d' % (300, 150, x, y))

        top_frame = tk.Frame(self.login)
        top_frame.pack(fill='x')
        login_label = tk.Label(top_frame, text="Please Login", font=('Arial', 12), bg='#e03c4c', fg='white', pady=10)
        login_label.pack(fill='x')

        form_frame = tk.Frame(self.login)
        form_frame.pack(padx=20, pady=10)

        tk.Label(form_frame, text="Username:").grid(row=0, column=0, sticky='w')
        username_entry = tk.Entry(form_frame)
        username_entry.grid(row=0, column=1, pady=(0, 10))
        username_entry.focus()

        tk.Label(form_frame, text="Password:").grid(row=1, column=0, sticky='w')
        password_entry = tk.Entry(form_frame, show="*")
        password_entry.grid(row=1, column=1)

        username_entry.bind("<Return>", lambda event: self.check_login(self.login, username_entry.get(), password_entry.get()))
        password_entry.bind("<Return>", lambda event: self.check_login(self.login, username_entry.get(), password_entry.get()))

        login_button = tk.Button(form_frame, text="Login", command=lambda: self.check_login(self.login, username_entry.get(), password_entry.get()))
        login_button.grid(row=2, column=0, columnspan=2, pady=10)

    def check_login(self, login, username, password):
        """Verifies user credentials and initializes chat components upon successful login."""
        try:
            connection = self.db_manager.get_connection()
            if not connection:
                raise Exception("Connection error. Try again.")

            cursor = connection.cursor()
            cursor.execute("SELECT password_hash, course_id FROM Users WHERE username = %s", (username,))
            result = cursor.fetchone()

            if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
                self.username = username
                self.course_id = result[1]
                login.destroy()
                self.master.deiconify()  # Show the main window
                self.setup_chat_widgets()  # Setup chat widgets now
                self.refresh_sessions_list()  # Refresh the sessions list to display upon login
            else:
                raise Exception("Login failed. Please check your credentials.")

        except Exception as e:
            messagebox.showerror("Login Error", str(e))

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

if __name__ == '__main__':
    root = tk.Tk()
    app = ChatbotApp(root)
    root.mainloop()
