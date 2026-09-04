import os
from io import BytesIO
from urllib.request import urlopen

import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


def cloudinary_configured() -> bool:
    if os.getenv("CLOUDINARY_URL"):
        return True
    return bool(
        os.getenv("CLOUDINARY_CLOUD_NAME")
        and os.getenv("CLOUDINARY_API_KEY")
        and os.getenv("CLOUDINARY_API_SECRET")
    )


def _configure():
    if os.getenv("CLOUDINARY_URL"):
        return
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )


def _resource_type(name: str) -> str:
    ext = os.path.splitext(name or "")[1].lower()
    if ext in {".pdf", ".xlsx", ".xls", ".csv", ".zip", ".doc", ".docx"}:
        return "raw"
    return "image"


def _split_name(name: str) -> tuple[str, str]:
    cleaned = (name or "").replace("\\", "/").lstrip("/")
    if ":" in cleaned.split("/")[0]:
        kind, public_id = cleaned.split(":", 1)
        return kind, public_id
    return _resource_type(cleaned), os.path.splitext(cleaned)[0]


@deconstructible
class CloudinaryMediaStorage(Storage):
    def __init__(self, folder="spars"):
        self.folder = folder.strip("/")
        _configure()

    def _save(self, name, content):
        upload_name = name.replace("\\", "/").lstrip("/")
        resource_type = _resource_type(upload_name)
        public_id = f"{self.folder}/{os.path.splitext(upload_name)[0]}"
        extra = {}
        ext = os.path.splitext(upload_name)[1].lstrip(".").lower()
        if ext:
            extra["format"] = ext
        result = cloudinary.uploader.upload(
            content,
            public_id=public_id,
            resource_type=resource_type,
            overwrite=True,
            **extra,
        )
        return f"{result['resource_type']}:{result['public_id']}"

    def url(self, name):
        resource_type, public_id = _split_name(name)
        return cloudinary.utils.cloudinary_url(
            public_id,
            resource_type=resource_type,
            secure=True,
        )[0]

    def exists(self, name):
        resource_type, public_id = _split_name(name)
        try:
            cloudinary.api.resource(public_id, resource_type=resource_type)
            return True
        except Exception:
            return False

    def delete(self, name):
        if not name:
            return
        resource_type, public_id = _split_name(name)
        try:
            cloudinary.uploader.destroy(public_id, resource_type=resource_type, invalidate=True)
        except Exception:
            pass

    def _open(self, name, mode="rb"):
        data = urlopen(self.url(name)).read()
        return File(BytesIO(data), name)

    def size(self, name):
        resource_type, public_id = _split_name(name)
        info = cloudinary.api.resource(public_id, resource_type=resource_type)
        return int(info.get("bytes") or 0)
