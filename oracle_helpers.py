# Import cx_Oracle for Oracle connectivity
try:
    import cx_Oracle
except ImportError:
    print("WARNING: cx_Oracle module not found. Oracle connectivity will not be available.")

def get_oracle_connection(username, password, host, port, service_name, sid=None):
    """
    Establish a connection to an Oracle database using either SERVICE_NAME or SID
    """
    import pdb
    pdb.set_trace()
    
    try:
        # Try to initialize Oracle client from LD_LIBRARY_PATH
        if hasattr(cx_Oracle, 'init_oracle_client'):
            try:
                # Use LD_LIBRARY_PATH environment variable if available
                cx_Oracle.init_oracle_client()
                print("Successfully initialized Oracle client using LD_LIBRARY_PATH")
            except Exception as e:
                print(f"Error initializing Oracle client: {e}")
                # Continue anyway, as the required libraries might be in the system path

        # Determine the connection string based on whether SID or SERVICE_NAME is provided
        if sid:
            dsn = cx_Oracle.makedsn(host, port, sid=sid)
        else:
            dsn = cx_Oracle.makedsn(host, port, service_name=service_name)
            
        # Connect to the Oracle database
        connection = cx_Oracle.connect(user=username, password=password, dsn=dsn)
        return connection, None
    except Exception as e:
        return None, str(e)
