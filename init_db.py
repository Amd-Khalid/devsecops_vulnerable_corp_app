import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Create Users Table (RBAC included)
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE, 
                  password TEXT, 
                  role TEXT)''')
                  
    # Create Posts Table (For CRUD operations)
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  author TEXT, 
                  content TEXT)''')

    # Insert default users (Vulnerability 1: Hardcoded, plaintext passwords - Good for SCA/SAST)
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('john_doe', 'password123', 'user')")
    
    # Insert dummy data
    c.execute("INSERT INTO posts (author, content) VALUES ('admin', 'Welcome to the corporate portal.')")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()