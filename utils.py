import pymysql

def getSettings():
    settings = {}
    with open('settings.txt', 'r') as file:
        for line in file:
            if line.strip():  # Ignore empty lines
                key, value = line.strip().split('=')
                settings[key] = value

    print(settings)
    return settings

def getConnection ():
    try:
        settings=getSettings()    
        # Establish a connection to the RDS instance
        conn = pymysql.connect(
            host=settings.get("host"),
            user=settings.get("user"),
            password=settings.get("password"),
            database=settings.get("leasemanagerdb"),
            connect_timeout=5
        )
        print("Connection successful!")
        # Create a cursor object
        cursor = conn.cursor()
        # Execute a simple query
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print("Database version:", version)
        return conn   
    except pymysql.MySQLError as e:
        print("Error connecting to the database:", e)

def closeConn(conn):
    conn.close()


def runQuery(query):
    try:
        conn=getConnection()
        conn=getConnection()
        cursor=conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        closeConn(conn)
        return result

    except pymysql.MySQLError as e:
        print("Error while executing query: ",e)

def get_anthropic_llm():
    try:
        llm = ChatAnthropic(model='claude-3-opus-20240229')
        log.info("**** Got Anthropic model")
        return llm
    except Exception as e:
        log.error(f"****Exception while getting anthropic: {e}")



if __name__== "__main__":
    query =input("testing sql query:  ")
    # query= "How are the important terms in the lease?"
    conn=getConnection()
    cursor=conn.cursor()
    cursor.execute(query);
    print("****** from db: ",cursor.fetchall())
