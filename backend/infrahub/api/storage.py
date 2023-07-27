import hashlib
import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile
from pydantic import BaseModel

from infrahub.api.dependencies import get_current_user
from infrahub.core import registry
from infrahub.log import get_logger

log = get_logger()
router = APIRouter(prefix="/storage")


class UploadResponse(BaseModel):
    identifier: str
    checksum: str


class UploadContentPayload(BaseModel):
    content: str


@router.get("/object/{identifier:str}")
async def get_file(
    identifier: str,
    _: str = Depends(get_current_user),
) -> Response:
    content = await registry.storage.retrieve(identifier=identifier)
    return Response(content=content)


@router.post("/upload/content")
async def upload_content(
    item: UploadContentPayload,
    _: str = Depends(get_current_user),
) -> UploadResponse:
    # TODO need to optimized how we read the content of the file, especially if the file is really large
    # Check this discussion for more details
    # https://stackoverflow.com/questions/63048825/how-to-upload-file-using-fastapi

    file_content = bytes(item.content, encoding="utf-8")
    identifier = str(uuid.uuid4())

    checksum = hashlib.md5(file_content).hexdigest()
    await registry.storage.store(identifier=identifier, content=file_content)
    return UploadResponse(identifier=identifier, checksum=checksum)


@router.post("/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    _: str = Depends(get_current_user),
) -> UploadResponse:
    # TODO need to optimized how we read the content of the file, especially if the file is really large
    # Check this discussion for more details
    # https://stackoverflow.com/questions/63048825/how-to-upload-file-using-fastapi

    file_content = file.file.read()
    identifier = str(uuid.uuid4())

    checksum = hashlib.md5(file_content).hexdigest()
    await registry.storage.store(identifier=identifier, content=file_content)
    return UploadResponse(identifier=identifier, checksum=checksum)