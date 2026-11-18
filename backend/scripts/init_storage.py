"""Create the S3/MinIO bucket if it doesn't exist. Idempotent."""
from app.services.storage import StorageClient


def main() -> None:
    StorageClient.from_settings().ensure_bucket()
    print("[init_storage] done")


if __name__ == "__main__":
    main()
