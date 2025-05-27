# Import mysql.connector for MySQL connectivity
try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    print("WARNING: mysql-connector-python module not found. MySQL connectivity will not be available.")
    MYSQL_AVAILABLE = False

def get_mysql_connection(username, password, host, port, database, charset='utf8mb4'):
    """
    Establish a connection to a MySQL database
    """
    if not MYSQL_AVAILABLE:
        return None, "mysql-connector-python module not available. Please install mysql-connector-python."
    
    try:
        # Validate required parameters
        if not all([username, host, port, database]):
            return None, "Missing required parameters: username, host, port, database"
        
        # Convert port to integer if it's a string
        try:
            port = int(port)
        except (ValueError, TypeError):
            return None, f"Invalid port number: {port}"

        # Connect to the MySQL database with timeout and additional configurations
        connection = mysql.connector.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            connection_timeout=30,  # 30 second timeout
            autocommit=True,
            charset=charset,
            use_unicode=True,
            sql_mode='STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'
        )
        
        return connection, None
    except Error as e:
        return None, f"MySQL Error: {str(e)}"
    except Exception as e:
        return None, f"Connection failed: {str(e)}"