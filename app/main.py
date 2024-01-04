from fastapi import FastAPI, Request, Depends, HTTPException, status
from starlette.responses import Response
import os
from tuya_connector import TuyaOpenAPI
import logging


app = FastAPI()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
ENDPOINT = "https://openapi.tuyaeu.com"
ACCESS_ID = os.environ.get('TUYA_ACCESS_ID')
ACCESS_KEY = os.environ.get('TUYA_ACCESS_KEY')
DEVICE_ID = "bf289bf7a00c812ce8mnvi"
API_KEY = os.environ.get('API_KEY')

def verify_api_key(api_key: str = None):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieautoryzowany dostęp"
        )
    return api_key
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
def jadziem(api_key: str = Depends(verify_api_key)):
    try:
        openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
        openapi.connect()
    except Exception as e:
        logging.error(f"Blad polaczenia z Tuya API: {e}")
        return Response(content=f"Blad laczenia z TuyaAPI: {e}", status_code=400)
    try:
        response = openapi.post(f'/v1.0/iot-03/devices/{DEVICE_ID}/commands',
                                body={"commands": [{"code": "temp_set", "value": 42}]})
        logging.info(f"response to:{response}")
        if response['success'] == True:
            return Response(content="Temperatura ustawiona", status_code=200)
        else:
            return Response(content="Blad ustawiania", status_code=400)
    except Exception as e:
        logging.error(f"Blad podczas wusylania danych z Tuya API: {e}")
        return Response(content=f"Blad ustawiania z powodu błedu: {e}", status_code=400)