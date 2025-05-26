# Import cx_Oracle for Oracle connectivity
try:
    import cx_Oracle
    ORACLE_AVAILABLE = True
except ImportError:
    print("WARNING: cx_Oracle module not found. Oracle connectivity will not be available.")
    ORACLE_AVAILABLE = False

def get_oracle_connection(username, password, host, port, service_name, sid=None):
    """
    Establish a connection to an Oracle database using either SERVICE_NAME or SID
    """
    if not ORACLE_AVAILABLE:
        return None, "cx_Oracle module not available. Please install cx_Oracle."
    
    try:
        # Validate required parameters
        if not all([username, host, port]):
            return None, "Missing required parameters: username, host, port"
        
        # Convert port to integer if it's a string
        try:
            port = int(port)
        except (ValueError, TypeError):
            return None, f"Invalid port number: {port}"

        # Try to initialize Oracle client from LD_LIBRARY_PATH
        if hasattr(cx_Oracle, 'init_oracle_client'):
            try:
                # Use LD_LIBRARY_PATH environment variable if available
                cx_Oracle.init_oracle_client()
                print("Successfully initialized Oracle client using LD_LIBRARY_PATH")
            except Exception as e:
                print(f"Oracle client already initialized or error: {e}")
                # Continue anyway, as the required libraries might be in the system path

        # Determine the connection string based on whether SID or SERVICE_NAME is provided
        if sid:
            dsn = cx_Oracle.makedsn(host, port, sid=sid)
        elif service_name:
            dsn = cx_Oracle.makedsn(host, port, service_name=service_name)
        else:
            return None, "Either SID or SERVICE_NAME must be provided"
            
        # Connect to the Oracle database with timeout
        connection = cx_Oracle.connect(
            user=username, 
            password=password, 
            dsn=dsn,
            timeout=30  # 30 second timeout
        )
        return connection, None
    except cx_Oracle.DatabaseError as e:
        error_obj, = e.args
        return None, f"Oracle Database Error: {error_obj.message}"
    except Exception as e:
        return None, f"Connection failed: {str(e)}"
