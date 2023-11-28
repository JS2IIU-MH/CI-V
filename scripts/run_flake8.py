""" run flake8 """

import sys
import subprocess

sys.path.append("./")


def _main(target) -> None:
    """
        Run the flake8 command.
    """
    # stdout: str = command_util.run_command(command=FLAKE8_COMMAND)
    stdout: str = subprocess.call(['flake8', '--max-line-length=100', target])
    if stdout != '':
        raise RuntimeError("There are flake8 errors or warning.")


if __name__ == '__main__':
    args = sys.argv
    _main(args[1])
