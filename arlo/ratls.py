import json
import aiohttp
import ssl
from . import Arlo
import os

class Ratls:

  def __init__(self, arlo: Arlo, device: str, cloud_id: str, ip: str, port: int) -> None:
    self._client = aiohttp.ClientSession()
    self._arlo = arlo
    self._device = device
    self._cloud_id = cloud_id
    self._ip = ip
    self._port = port

    certs_path = arlo.security.certs_path
    device_certs_path = arlo.security.device_certs_path(f"{arlo.user_id}_{self._device}")


    """
    The web server on the base station uses client authentication certificates
    as well as the JWT and somehow they are connected together.
    """
    self._sslcontext = ssl.create_default_context(cafile=os.path.join(certs_path, "ica.crt"), purpose=ssl.Purpose.CLIENT_AUTH)
    self._sslcontext.load_cert_chain(os.path.join(device_certs_path, "peer.crt"), arlo.security.private_key_path)

  async def teardown(self):
    await self._client.close()

  @property
  def url(self):
    return f"https://{self._ip}:{self._port}/hmsls"

  async def refresh_token(self) -> None:
    "This fetches a JWT used to authorize to the web server in the base station."
    data = await self._arlo.server_get(f"/hmsweb/users/device/ratls/token/{self._device}")
    self._token = data["ratlsToken"]


  async def open_port(self) -> bool:
    """
    This notifies the base station to open the ratls port.
    It only stays open for 5 mins after last activity and needs to be opened again after that.
    An event message comes back to the subscibe SSE when it has opened and contains the
    public and private IP and the port number used.
    """
    return await self._arlo.notify_device(self._device, self._cloud_id, "open", "storage/ratls", False)

  async def get_recordings(self, start: str, end: str):
    response = await self._client.get(
      f"{self.url}/list/{start}/{end}",
      ssl=self._sslcontext,
      headers={
        "Authorization": f"Bearer {self._token}",
        "Accept": "application/json"
      }
    )

    if response.status != 200:
      print(await response.text())
      raise Exception("Could not get recordings")

    json_data = json.loads(await response.text())

    return json_data["data"]

  async def download_recording(self, path: str):
    response = await self._client.get(
      f"{self.url}/download/{path}",
      ssl=self._sslcontext,
      headers={
        "Authorization": f"Bearer {self._token}"
      }
    )

    if response.status != 200:
      print(await response.text())
      raise Exception("Error downloading recording")

    paths = path.split("/")[0:-1]

    os.makedirs(os.path.join(self._arlo.storage_dir, "recordings", *paths), exist_ok=True)
    with open(os.path.join(self._arlo.storage_dir, "recordings", path), "wb") as file:
      async for data in response.content.iter_chunked(1024):
        file.write(data)
