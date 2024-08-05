import json, boto3, requests, pymysql, threading, time
from utilities import MySQL_Writer, NameDumper, GameDumper, PlayerDumper, DataDumper

def get_secret():
    secret_name = "Mysql/password"
    region_name = "us-west-1"
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        return get_secret_value_response['SecretString'][32:46]
    except Exception as e:
        print(f"Error retrieving password: {e}")
        raise

#configuration variables
url = "https://api-nba-v1.p.rapidapi.com"
headers = {
    'x-rapidapi-key': "b990592d51msh5e1029396589d1bp18dd72jsnce5f8c3e8b6c",
    'x-rapidapi-host': "api-nba-v1.p.rapidapi.com"
}
pw = get_secret()
connection = pymysql.connect(
    host='yba-database.c30igyqguxod.us-west-1.rds.amazonaws.com', 
    user='admin', 
    password=pw, 
    database='yba'
)

def dumpJson(data, testFile):
    if not isinstance(testFile, str):
        print("testFile parameter must be of type string")
        return False
    try:
        with open(testFile, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Could not dump into json file with exception {e}")
        return False

def getData(endpoint):
    try:
        response = requests.get(url + endpoint, headers=headers)
    except Exception as e:
        print(f"Could not fetch data with endpoint {endpoint}")
        return None
    
    if (response.status_code == 200):
        return response.json()
    print(f"Could not fetch data with endpoint {endpoint} with status code {response.status_code}")
    return None

def lambda_handler(event, context):
    try:
        #gets most recent season
        season = getData("/seasons")['response'][-1]

        nd = NameDumper(season)
        nd.dumpData()
        gd = GameDumper(season)
        gd.dumpData()
        pd = PlayerDumper(season)
        pd.dumpData()
        
        #transfer data to MySQL, updating games and player data in version2 under most recent season
        sqlWriter = MySQL_Writer("games", connection, season)
        sqlWriter.transferData()
        sqlWriter.setTable("version2")
        sqlWriter.transferData()
        sqlWriter.normalizeOPI()
        
        if connection:
            connection.close()
        
        return {
            'statusCode': 200,
            'body': 'Data uploaded successfully'
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error uploading file: {e}'
        }

if __name__ == "__main__":
    test = MySQL_Writer("version2", 2023)
    test.normalizeOPI()
    # columns = ['hi', 'im', 'fat']
    # update_clause = ', '.join([f"{col} = VALUES({col})" for col in columns])
    # print(update_clause)