from valutatrade_hub.cli.interface import cli
from valutatrade_hub.logging_config import setup_logging


def main():
    setup_logging()
    cli()


if __name__ == "__main__":
    main()
