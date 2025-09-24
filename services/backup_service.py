"""Backup service for database backup and restore operations."""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlmodel import Session

from app.config import Settings
from app.db import get_engine
from utils.errors import ServiceError


class BackupService:
    """Service for database backup and restore operations."""

    @classmethod
    def create_backup(cls, settings: Settings) -> dict[str, Any]:
        """
        Create a backup of the current database.

        Args:
            settings: Application settings

        Returns:
            Dictionary with backup information
        """
        try:
            # Get current database path
            db_path = Path(settings.db_path)
            if not db_path.exists():
                raise ServiceError("Database file not found")

            # Create backup filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"coach_app_backup_{timestamp}.db"

            # Create backup in temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                backup_path = temp_path / backup_filename

                # Copy database file
                shutil.copy2(db_path, backup_path)

                # Read backup content
                with open(backup_path, "rb") as f:
                    backup_content = f.read()

            return {
                "filename": backup_filename,
                "content": backup_content,
                "size": len(backup_content),
                "created_at": datetime.utcnow(),
                "original_db_path": str(db_path),
            }

        except Exception as e:
            raise ServiceError(f"Backup creation failed: {str(e)}") from e

    @classmethod
    def restore_backup(
        cls, settings: Settings, backup_file: UploadFile
    ) -> dict[str, Any]:
        """
        Restore database from backup file.

        Args:
            settings: Application settings
            backup_file: Uploaded backup file

        Returns:
            Dictionary with restore information
        """
        try:
            # Validate file type
            if (not backup_file.filename
                    or not backup_file.filename.endswith('.db')):
                raise ServiceError("Backup file must be a .db file")

            # Read backup content
            backup_content = backup_file.file.read()
            if len(backup_content) == 0:
                raise ServiceError("Backup file is empty")

            # Get current database path
            db_path = Path(settings.db_path)
            db_dir = db_path.parent

            # Ensure database directory exists
            db_dir.mkdir(parents=True, exist_ok=True)

            # Create backup of current database before restore
            current_backup_path = None
            if db_path.exists():
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                current_backup_filename = f"pre_restore_backup_{timestamp}.db"
                current_backup_path = db_dir / current_backup_filename
                shutil.copy2(db_path, current_backup_path)

            # Write new database content
            with open(db_path, "wb") as f:
                f.write(backup_content)

            # Verify the restored database is valid
            try:
                engine = get_engine(settings)
                with Session(engine) as session:
                    # Try to execute a simple query to verify database integrity
                    session.exec("SELECT 1")
            except Exception as e:
                # Restore failed, try to restore the previous backup
                if current_backup_path and current_backup_path.exists():
                    shutil.copy2(current_backup_path, db_path)
                    current_backup_path.unlink()  # Clean up temp backup
                raise ServiceError(
                    f"Restored database is invalid: {str(e)}"
                ) from e

            # Clean up temporary backup if restore was successful
            if current_backup_path and current_backup_path.exists():
                current_backup_path.unlink()

            return {
                "success": True,
                "restored_at": datetime.utcnow(),
                "backup_filename": backup_file.filename,
                "backup_size": len(backup_content),
                "database_path": str(db_path),
            }

        except ServiceError as e:
            raise e
        except Exception as e:
            raise ServiceError(f"Backup restore failed: {str(e)}") from e

    @classmethod
    def validate_backup_file(cls, backup_file: UploadFile) -> dict[str, Any]:
        """
        Validate a backup file without restoring it.

        Args:
            backup_file: Uploaded backup file

        Returns:
            Dictionary with validation results
        """
        try:
            # Validate file type
            if (not backup_file.filename
                    or not backup_file.filename.endswith('.db')):
                return {
                    "valid": False,
                    "error": "File must be a .db file"
                }

            # Read first few bytes to check if it's a valid SQLite file
            backup_file.file.seek(0)
            header = backup_file.file.read(16)
            backup_file.file.seek(0)  # Reset file pointer

            # SQLite files start with "SQLite format 3"
            if not header.startswith(b"SQLite format 3"):
                return {
                    "valid": False,
                    "error": "File is not a valid SQLite database"
                }

            # Get file size
            backup_file.file.seek(0, 2)  # Seek to end
            file_size = backup_file.file.tell()
            backup_file.file.seek(0)  # Reset file pointer

            return {
                "valid": True,
                "filename": backup_file.filename,
                "size": file_size,
                "message": "Backup file appears to be valid"
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation failed: {str(e)}"
            }

    @classmethod
    def get_database_info(cls, settings: Settings) -> dict[str, Any]:
        """
        Get information about the current database.

        Args:
            settings: Application settings

        Returns:
            Dictionary with database information
        """
        try:
            db_path = Path(settings.db_path)
            
            if not db_path.exists():
                return {
                    "exists": False,
                    "path": str(db_path),
                    "size": 0,
                    "created_at": None,
                    "modified_at": None,
                }

            stat = db_path.stat()
            
            return {
                "exists": True,
                "path": str(db_path),
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
                "modified_at": datetime.fromtimestamp(stat.st_mtime),
            }

        except Exception as e:
            raise ServiceError(f"Failed to get database info: {str(e)}") from e

    @classmethod
    def cleanup_old_backups(cls, settings: Settings, keep_days: int = 30) -> dict[str, Any]:
        """
        Clean up old backup files.

        Args:
            settings: Application settings
            keep_days: Number of days to keep backups

        Returns:
            Dictionary with cleanup results
        """
        try:
            db_dir = Path(settings.db_path).parent
            backup_pattern = "coach_app_backup_*.db"
            pre_restore_pattern = "pre_restore_backup_*.db"

            cleaned_files = []
            total_size_freed = 0
            
            # Find and clean up old backup files
            for pattern in [backup_pattern, pre_restore_pattern]:
                for backup_file in db_dir.glob(pattern):
                    try:
                        # Check file age
                        file_age = (
                            datetime.utcnow().timestamp() -
                            backup_file.stat().st_mtime
                        )
                        age_days = file_age / (24 * 60 * 60)
                        
                        if age_days > keep_days:
                            file_size = backup_file.stat().st_size
                            backup_file.unlink()
                            cleaned_files.append(backup_file.name)
                            total_size_freed += file_size
                    except Exception:
                        # Skip files that can't be processed
                        continue

            return {
                "cleaned_files": cleaned_files,
                "files_removed": len(cleaned_files),
                "size_freed": total_size_freed,
                "keep_days": keep_days,
            }

        except Exception as e:
            raise ServiceError(f"Backup cleanup failed: {str(e)}") from e
