# Arlo Remote Access to Local Storage (RATLS)

This is a POC repo to show how to gain access to the local storage server running on a base station that has a usb or sd card and supports RATLS.

It needs no external data, apart from 2FA approvals if needed on the account and will allow you to download the mp4 video recordings.

The main script needs some configuration variables at the top, but the intention of this
code is to be (hopefully) merged/added into [pyaarlo](https://github.com/twrecked/pyaarlo) and [hass-aarlo](https://github.com/twrecked/hass-aarlo)
