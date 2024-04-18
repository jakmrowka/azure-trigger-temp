from fastapi import FastAPI, Request, Depends, HTTPException, status, Header
from starlette.responses import Response
import os
from tuya_connector import TuyaOpenAPI
import logging
import yaml
from datetime import date, timedelta
from elasticsearch import Elasticsearch

app = FastAPI()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
ENDPOINT = "https://openapi.tuyaeu.com"
ACCESS_ID = os.environ.get('TUYA_ACCESS_ID')
ACCESS_KEY = os.environ.get('TUYA_ACCESS_KEY')
DEVICE_TYPE = os.environ.get('DEVICE_TYPE')
API_KEY = os.environ.get('API_KEY')

es_host = os.environ.get('ES_HOST', 'localhost')
es_port = os.environ.get('ES_PORT', '9200')
es_username = os.environ.get('ES_USERNAME')
es_password = os.environ.get('ES_PASSWORD')
index_name = os.environ.get('ES_INDEX', 'index_name')

file_path = 'list_device'
with open(file_path, 'r') as file:
    text_data = yaml.safe_load(file)
data = yaml.safe_load(text_data)
DEVICE_ID = data.get(DEVICE_TYPE)[0]


# def verify_api_key(api_key: str = None):
#     if api_key != API_KEY:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Nieautoryzowany dostęp"
#         )
#     return api_key

def get_api_key(api_key: str = Header(...)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Nieautoryzowany dostep")
    return api_key

def get_average_temperature_for_today():
    try:
        es = Elasticsearch(es_host + ":" + es_port, basic_auth=(es_username, es_password))
    except Exception as e:
        logging.error(f"Błąd połączenia z Elasticsearch: {e}")
    today = date.today()
    tomorrow = today + timedelta(days=1)
    response = es.search(index=index_name, body={
        "query": {
            "bool": {
                "must": [
                    {"range": {"timestamp": {"gte": today.strftime("%Y-%m-%dT00:00:00"), "lt": tomorrow.strftime("%Y-%m-%dT00:00:00")}}}
                ]
            }
        },
        "aggs": {
            "average_temperature": {
                "avg": {
                    "field": "biezaca_temp"
                }
            }
        },
        "size": 0  # Nie potrzebujemy żadnych dokumentów, tylko agregacje
    })
    if response.get('aggregations', {}).get('average_temperature', {}).get('value') is not None:
        return response['aggregations']['average_temperature']['value']
    else:
        return None


@app.get("/info")
async def read_request_info(request: Request):
    request_info = {
        "client_host": request.client.host,
        "client_port": request.client.port,
        "url_path": str(request.url.path),
        "method": request.method,
        "query_params": dict(request.query_params),
        "headers": dict(request.headers),
        "cookies": request.cookies,
    }

    return request_info

@app.get("/ready")
def ready():
    return Response(content="Serwer gotowy", status_code=200)

@app.get("/jadziem")
# def jadziem(api_key: str = Depends(verify_api_key)):
def jadziem(api_key: str = Depends(get_api_key)):
    try:
        openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
        openapi.connect()
    except Exception as e:
        logging.error(f"Blad polaczenia z Tuya API: {e}")
        return Response(content=f"Blad laczenia z TuyaAPI: {e}", status_code=400)
    average_temp = get_average_temperature_for_today()
    if average_temp is not None and average_temp < 19:
        try:
            response = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_ID}/commands',
                                    body={"commands":[{"code":"TempSet","value":42},{"code":"Mode","value":"0"}]})
            logging.info(f"response to:{response}")
            if response['success'] == True:
                return Response(content="Temperatura ustawiona, wlaczam grzanie", status_code=200)
            else:
                return Response(content="Blad ustawiania", status_code=400)
        except Exception as e:
            logging.error(f"Blad podczas wusylania danych z Tuya API: {e}")
            return Response(content=f"Blad ustawiania z powodu błedu: {e}", status_code=400)
    elif average_temp is None:
        return Response(content=f"Nie wlaczam grzania. Nie wiem czy jest cieplo", status_code=200)
    else:
        return Response(content=f"Zbyt cieplo, jest srednio: {round(average_temp,2)} stopni. Nie wlaczam grzania", status_code=200)
