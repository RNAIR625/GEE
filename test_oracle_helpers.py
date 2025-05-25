import cx_Oracle
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('oracle_helpers')

def get_oracle_connection(username, password, host, port, service_name, timeout=10):
    """
    Establishes a connection to an Oracle database using the provided credentials.
    
    Args:
        username (str): Oracle database username
        password (str): Oracle database password
        host (str): Hostname or IP address of the Oracle server
        port (str or int): Port number for the Oracle listener
        service_name (str): Oracle service name or SID
        timeout (int): Connection timeout in seconds
    
    Returns:
        tuple: (connection_object, error_message)
            - If successful, returns (connection, None)
            - If failed, returns (None, error_message)
    """
    connection = None
    error = None
    
    try:
        # Import cx_Oracle or oracledb - handle both old and new versions
        try:
            import cx_Oracle as oracle_client
            logger.info("Using cx_Oracle client")
        except ImportError:
            try:
                import oracledb as oracle_client
                # Enable thick mode for oracledb if available
                if hasattr(oracle_client, 'init_oracle_client'):
                    try:
                        oracle_client.init_oracle_client()
                        logger.info("Initialized oracle client in thick mode")
                    except Exception as e:
                        logger.warning(f"Could not initialize oracle client in thick mode: {e}")
            except ImportError:
                return None, "Oracle client library (cx_Oracle or oracledb) not installed"
        
        # Log connection attempt (without password)
        logger.info(f"Attempting to connect to Oracle DB: {username}@{host}:{port}/{service_name}")
        
        # Format the connection string based on service_name or SID
        if '/' in service_name:  # If using a service name with path like "orcl/pdb1"
            dsn = f"{host}:{port}/{service_name}"
        else:
            # Create a DSN (Data Source Name) for the connection
            try:
                # First try the makedsn approach
                dsn = oracle_client.makedsn(host=host, port=port, service_name=service_name)
            except AttributeError:
                # If makedsn is not available, use the string format directly
                dsn = f"{host}:{port}/{service_name}"
        
        # Attempt to establish connection
        start_time = time.time()
        
        connection = oracle_client.connect(
            user=username,
            password=password,
            dsn=dsn,
            encoding="UTF-8"
        )
        
        elapsed_time = time.time() - start_time
        
        # Log successful connection
        logger.info(f"Successfully connected to Oracle DB in {elapsed_time:.2f}s")
        
    except Exception as e:
        # Handle exceptions
        error = str(e)
        logger.error(f"Error connecting to Oracle: {error}")
        
        # Check for common issues and provide helpful messages
        if "DPI-1047" in error:
            error = "Oracle Client library not found. Please install Oracle Instant Client."
        elif "DPI-1072" in error:
            error = "Oracle Client and Server versions are not compatible."
        elif "TNS" in error:
            error = f"TNS connection error: {error}. Check host, port, and service name."
        elif "ORA-01017" in error:
            error = "Invalid username/password. Please check your credentials."
        elif "ORA-12514" in error:
            error = f"Service name '{service_name}' not found. Check your service name."
        elif "ORA-12541" in error:
            error = f"No listener on host '{host}' port {port}. Check your network settings."
        elif "ORA-24408" in error:
            error = "Could not generate unique server group name."
            
    return connection, error

def execute_oracle_query(connection, query, params=None, fetch_all=True):
    """
    Executes a query on an Oracle database and returns the results.
    
    Args:
        connection: Oracle connection object
        query (str): SQL query to execute
        params (dict, optional): Parameters for the query
        fetch_all (bool): If True, fetches all rows; if False, fetches one row
    
    Returns:
        tuple: (results, error_message)
            - If successful, returns (query_results, None)
            - If failed, returns (None, error_message)
    """
    cursor = None
    results = None
    error = None
    
    try:
        cursor = connection.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        if fetch_all:
            results = cursor.fetchall()
        else:
            results = cursor.fetchone()
            
    except Exception as e:
        error = str(e)
        logger.error(f"Error executing Oracle query: {error}")
        
    finally:
        if cursor:
            cursor.close()
            
    return results, error

def test_oracle_connection(username, password, host, port, service_name):
    """
    Tests a connection to an Oracle database and returns server date if successful.
    
    Args:
        username (str): Oracle database username
        password (str): Oracle database password
        host (str): Hostname or IP address of the Oracle server
        port (str or int): Port number for the Oracle listener
        service_name (str): Oracle service name or SID
    
    Returns:
        dict: Result dictionary containing:
            - success (bool): Whether the connection was successful
            - message (str): Success or error message
            - server_date (str, optional): Oracle server date if successful
    """
    result = {
        'success': False,
        'message': '',
        'server_date': None
    }
    
    # Establish connection
    connection, error = get_oracle_connection(
        username=username,
        password=password,
        host=host,
        port=port,
        service_name=service_name
    )
    
    if error:
        result['message'] = f'Oracle connection error: {error}'
        return result
    
    try:
        # Test query to get Oracle server date
        query = "SELECT TO_CHAR(SYSDATE, 'YYYY-MM-DD HH24:MI:SS') AS SERVER_DATE FROM DUAL"
        data, error = execute_oracle_query(connection, query, fetch_all=False)
        
        if error:
            result['message'] = f'Error executing test query: {error}'
        else:
            server_date = data[0] if data else "Unknown"
            result['success'] = True
            result['message'] = f'Oracle connection successful! Server date: {server_date}'
            result['server_date'] = server_date
            
    finally:
        # Close the connection
        if connection:
            try:
                connection.close()
                logger.info("Oracle connection closed")
            except Exception as e:
                logger.error(f"Error closing Oracle connection: {e}")
    
    return result

def get_oracle_tables(connection, owner=None):
    """
    Gets a list of tables from an Oracle database.
    
    Args:
        connection: Oracle connection object
        owner (str, optional): Schema owner to filter tables
    
    Returns:
        tuple: (tables_list, error_message)
            - If successful, returns (tables, None)
            - If failed, returns (None, error_message)
    """
    query = """
    SELECT 
        OWNER, 
        TABLE_NAME, 
        TABLESPACE_NAME,
        STATUS,
        NUM_ROWS
    FROM 
        ALL_TABLES
    """
    
    params = {}
    
    if owner:
        query += " WHERE OWNER = :owner"
        params['owner'] = owner.upper()
    else:
        query += " WHERE OWNER NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'DIP', 'ORACLE_OCM', 'DBSNMP')"
    
    query += " ORDER BY OWNER, TABLE_NAME"
    
    return execute_oracle_query(connection, query, params)

def get_oracle_table_columns(connection, table_name, owner=None):
    """
    Gets column information for a specific table in an Oracle database.
    
    Args:
        connection: Oracle connection object
        table_name (str): Name of the table
        owner (str, optional): Schema owner of the table
    
    Returns:
        tuple: (columns_list, error_message)
            - If successful, returns (columns, None)
            - If failed, returns (None, error_message)
    """
    query = """
    SELECT 
        COLUMN_NAME, 
        DATA_TYPE,
        DATA_LENGTH,
        DATA_PRECISION,
        DATA_SCALE,
        NULLABLE,
        COLUMN_ID
    FROM 
        ALL_TAB_COLUMNS
    WHERE 
        TABLE_NAME = :table_name
    """
    
    params = {'table_name': table_name.upper()}
    
    if owner:
        query += " AND OWNER = :owner"
        params['owner'] = owner.upper()
    
    query += " ORDER BY COLUMN_ID"
    
    return execute_oracle_query(connection, query, params)

# Example usage
if __name__ == "__main__":
    # Example - Test connection
    test_result = test_oracle_connection(
        username="rnair",
        password="amdocs",
        host="localhost",
        port=1521,
        service_name="xe"
    )
    
    print(f"Connection test result: {test_result['success']}")
    print(f"Message: {test_result['message']}")
    
    if test_result['success']:
        print(f"Oracle server date: {test_result['server_date']}")