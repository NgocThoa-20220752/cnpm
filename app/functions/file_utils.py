import os
import uuid
import logging
from fastapi import UploadFile
from PIL import Image
from app.core.config import get_settings
from app.exceptions import BadRequestException

settings = get_settings()
logger = logging.getLogger(__name__)


class FileUtils:
    """Utility functions for file handling"""

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """Validate if file extension is allowed"""
        if not filename or '.' not in filename:
            return False
        extension = filename.split(".")[-1].lower()
        return extension in settings.allowed_extensions_list

    @staticmethod
    def validate_file_size(file: UploadFile) -> bool:
        """Validate if file size is within limit"""
        # Ưu tiên sử dụng content length từ header
        if hasattr(file, 'size') and file.size:
            return file.size <= settings.MAX_UPLOAD_SIZE

        # Fallback: sử dụng seek/tell
        current_pos = file.file.tell()
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(current_pos)
        return file_size <= settings.MAX_UPLOAD_SIZE

    @staticmethod
    async def save_upload_file(file: UploadFile, subfolder: str = "") -> str:
        """
        Save uploaded file and return the file path
        """
        if not FileUtils.validate_file_extension(file.filename):
            raise BadRequestException("File type not allowed")

        if not FileUtils.validate_file_size(file):
            raise BadRequestException("File size exceeds maximum limit")

        # Prevent path traversal
        subfolder = subfolder.strip('/\\')
        if '..' in subfolder or subfolder.startswith('/'):
            raise BadRequestException("Invalid subfolder path")

        # Generate unique filename
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"

        # Create directory if not exists
        upload_path = os.path.join(settings.UPLOAD_DIR, subfolder)
        os.makedirs(upload_path, exist_ok=True)

        # Save file
        file_path = os.path.join(upload_path, unique_filename)
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            logger.error(f"Failed to save file {file_path}: {str(e)}")
            raise BadRequestException("Failed to save file")

        return os.path.join(subfolder, unique_filename).replace("\\", "/")

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete a file"""
        try:
            full_path = os.path.join(settings.UPLOAD_DIR, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
            return False

    @staticmethod
    async def save_image_with_thumbnail(
            file: UploadFile,
            subfolder: str = "products",
            thumbnail_size: tuple[int, int] = (300, 300)  # ✅ Đã sửa
    ) -> dict:
        """
        Save image and create thumbnail
        Returns dict with 'original' and 'thumbnail' paths
        """
        original_path = None
        try:
            # Save original
            original_path = await FileUtils.save_upload_file(file, subfolder)

            # Create thumbnail
            full_original_path = os.path.join(settings.UPLOAD_DIR, original_path)
            thumbnail_filename = f"thumb_{os.path.basename(original_path)}"
            thumbnail_path = os.path.join(settings.UPLOAD_DIR, subfolder, thumbnail_filename)

            with Image.open(full_original_path) as img:
                img.thumbnail(thumbnail_size)
                img.save(thumbnail_path)

            return {
                "original": original_path,
                "thumbnail": os.path.join(subfolder, thumbnail_filename).replace("\\", "/")
            }
        except Exception as e:
            # Clean up on error
            if original_path and os.path.exists(os.path.join(settings.UPLOAD_DIR, original_path)):
                FileUtils.delete_file(original_path)
            logger.error(f"Failed to process image: {str(e)}")
            raise BadRequestException(f"Failed to process image: {str(e)}")