from typing import Tuple
import aiohttp
import base64
import time
import random

from .const import AUTH_HOST, HOST
from .security_utils import SecurityUtils

class Arlo:
  def __init__(self, device_id: str, storage_dir: str = "./", client: aiohttp.ClientSession = None, debug: bool = False) -> None:
    self._client = client or aiohttp.ClientSession()
    self._debug = debug
    self._device_id = device_id
    self._user_id: str = None
    self._security = SecurityUtils(storage_dir)
    self._storage_dir = storage_dir

  async def teardown(self) -> None:
    await self._client.close()

  @property
  def storage_dir(self):
    return self._storage_dir

  @property
  def security(self):
    return self._security

  @property
  def user_id(self) -> str:
    return self._user_id

  async def login(self, email, password) -> None:
    response = await self._client.post(
      f"{AUTH_HOST}/api/auth",
      headers={
        "Referer": AUTH_HOST,
      },
      json={
        "email": email,
        "password": password
      }
    )

    if response.status != 200:
      raise Exception("Invalid credentials")

    json = await response.json()
    if self._debug:
      print(json)
    self._token: str = json["data"]["token"]
    self._token64: str = base64.b64encode(self._token.encode("utf-8")).decode("utf-8")

    self._user_id: str = json["data"]["userId"]

    if not json["data"]["authCompleted"]:
      factors = await self._get_factors()
      factor = None
      for f in factors:
        if f["factorRole"] == "PRIMARY":
          factor = f
          break

      factor_auth_code = await self._start_auth(factor["factorId"])

      while True:
        success, retry = await self._finish_auth(factor_auth_code)
        if success:
          return
        if not retry:
          raise Exception("Could not authenticate with MFA")
        time.sleep(1)



  async def _get_factors(self):
    response = await self._client.get(
      f"{AUTH_HOST}/api/getFactors?data={time.time()}",
      headers={
        "Authorization": self._token64,
        "Referer": AUTH_HOST,
      }
    )
    json = await response.json()
    if self._debug:
      print(json)
    return json["data"]["items"]

  async def _start_auth(self, factor_id: str) -> str:
    response = await self._client.post(
      f"{AUTH_HOST}/api/startAuth",
      headers={
        "Authorization": self._token64,
        "Referer": AUTH_HOST,
      },
      json={
        "factorId": factor_id,
      },
    )

    if response.status != 200:
      raise Exception("Could not start MFA")

    json = await response.json()
    if self._debug:
      print(json)
    return json["data"]["factorAuthCode"]

  async def _finish_auth(self, factor_auth_code: str) -> Tuple[bool, bool]:
    response = await self._client.post(
      f"{AUTH_HOST}/api/finishAuth",
      headers={
        "Authorization": self._token64,
        "Referer": AUTH_HOST,
      },
      json={
        "factorAuthCode": factor_auth_code,
      }
    )

    if response.status != 200:
      raise Exception("Error while finishing MFA")

    json = await response.json()
    if self._debug:
      print(json)
    if json["meta"]["code"] == 400:
      if json["meta"]["error"] == 9233:
        return False, True
      elif json["meta"]["error"] == 9238:
        return False, False
    elif json["meta"]["code"] == 200:
      if json["data"]["authCompleted"]:
        self._token = json["data"]["token"]
        return True, False


    return False, False

  async def notify_device(self, device: str, cloudId: str, action:str, resource: str, publish: bool = True) -> bool:
    transId = random.randint(90000000,100000000)
    response = await self._client.post(
      f"{HOST}/hmsweb/users/devices/notify/{device}",
      headers={
        "Authorization": self._token,
        "auth-version": "2",
        "xcloudId": cloudId,
      },
      json={
        "action": action,
        "resource": resource,
        "from": self._user_id,
        "transId": f"web!{transId}!{time.time()}",
        "to": device,
        "publishResponse": publish
      }
    )


    if self._debug:
      print(response)

    if response.status != 200:
      return False

    json = await response.json()
    if self._debug:
      print(json)
    return json["success"]

  async def server_get(self, path):
    response = await self._client.get(
      f"{HOST}{path}",
      headers={
        "Authorization": self._token,
        "auth-version": "2",
      }
    )
    if response.status != 200:
      raise Exception(f"Error getting {path}", await response.text())
    json = await response.json()
    return json["data"]

  async def check_device_certs(self, base_station_id: str):
    if not self._security.has_device_certs(base_station_id):
      response = await self._client.post(
        f"{HOST}/hmsweb/users/devices/v2/security/cert/create",
        headers={
          "auth-version": "2",
          "Authorization": self._token,
        },
        json={
          "uuid": self._device_id,
          "publicKey": self._security.public_key.replace("\n", "").replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", ""),
          "uniqueIds": [
            base_station_id,
          ]
        }
      )

      if response.status != 200:
        print(await response.json())
        raise Exception("Error getting certs")

      json = await response.json()
      self._security.save_device_certs(base_station_id, json["data"])
