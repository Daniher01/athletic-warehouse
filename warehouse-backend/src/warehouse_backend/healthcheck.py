import sys
import urllib.request


def main() -> None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=3) as resp:
            if resp.status == 200:
                sys.exit(0)
    except Exception:
        sys.exit(1)
    sys.exit(1)


if __name__ == "__main__":
    main()
