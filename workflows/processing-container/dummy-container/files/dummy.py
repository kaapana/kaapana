import pydicom
import os


if __name__ == "__main__":

    print("Dummy container started.")
    if os.environ['CONTAINER_NUMBER']:
        container_number = os.environ['CONTAINER_NUMBER']
        print("This is container number " + container_number)

    exit(0)
