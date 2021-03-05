import sys
import asyncio

from . import Arlo
from .ratls import Ratls
import time

EMAIL = "<YOUR EMAIL>"
PASSWORD = "<YOUR PASSWORD>"

# This should be a random, but static id per installation.
# The android app uses the device identifier UUID for this value.
# It can be any string at all.
DEVICE_ID = "6c58c859-10e2-4b2f-b2cb-1b4a8bdecafa"

# These values can come from the devices list/base station instance
BASE_STATION_ID = "<device.id>"
BASE_STATION_CLOUD_ID = "<device.cloudId>"

# When ratls.open_port() is called, these values actually come in a SSE event message,
# at which point the port is now open ready to take connections.
BASE_STATION_IP = "192.168.X.X"
BASE_STATION_RATLS_PORT = 00000

START_DATE = "20210304"
END_DATE = "20210304"


async def initialise() -> None:
  try:
    arlo = Arlo(device_id=DEVICE_ID, storage_dir="./storage/", debug=True)
    await arlo.login(EMAIL, PASSWORD)

    await arlo.check_device_certs(f"{arlo.user_id}_{BASE_STATION_ID}")

    ratls = Ratls(arlo, BASE_STATION_ID, BASE_STATION_CLOUD_ID, BASE_STATION_ID, BASE_STATION_RATLS_PORT)
    await ratls.refresh_token()
    open = await ratls.open_port()
    if open:
      time.sleep(5)
      recordings = await ratls.get_recordings(START_DATE, END_DATE)
      print(recordings[0])
      path = recordings[0]["presignedContentUrl"]
      await ratls.download_recording(path)
    else:
      raise Exception("Could not open storage port")

  except Exception as e:
    print("Exception")
    print(e)

  finally:
    await arlo.teardown()
    await ratls.teardown()


def main():
  try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initialise())
  except KeyboardInterrupt:
    return 1


if __name__ == "__main__":
    sys.exit(main())
