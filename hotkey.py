import subprocess
import keyboard


# sudo apt install parrot-tools-qdronectrl
# qdronectrl


def photo() -> None:
    """using keyboard to take photos,
    pay attention to the interpreter environment.
    """

    dirname = "images/meta"
    cmd = f"sphinx-cli camera front_streaming -n --count=1 -o '{dirname}'"
    subprocess.run(cmd, shell=True)


keyboard.add_hotkey("f9", photo)
keyboard.wait()
