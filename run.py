import argparse
from wos import create_wos_account


def main():
    parser = argparse.ArgumentParser(description="Tools for making it rain")
    parser.add_argument('command', help='Command to run')
    parser.add_argument('value', help='Value for the command')
    args = parser.parse_args()

    if args.command == 'init':
        if args.value == 'wos':
            create_wos_account()


if __name__ == '__main__':
    main()
