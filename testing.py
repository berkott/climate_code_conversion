import docker
import tempfile
import os
import re


def _extract_pytest_output(output):
    """
    Get everything after ============================= test session starts ============================== (including that line)
    """

    result = re.split(r"={2,}\stest session starts\s={2,}", output)[1]

    return f"============================= test session starts ==============================\n{result}"


def _run_tests_in_docker(source_code, docker_image):
    """
    Run unit tests on the given source code and return the output.
    Uses Docker in case we need to install dependencies.

    """
    # Initialize Docker client
    client = docker.from_env()

    # Pull the Python Docker image
    print(f"Pulling Docker image {docker_image}...")
    client.images.pull(docker_image)

    test_dir = os.getcwd() + "/tests"

    # Create a temporary file and write the test code to it
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, dir=test_dir) as temp:
        temp.write(source_code.encode("utf-8"))
        temp_filename = temp.name


    # Define the commands to run
    commands = f"""
    pip install pytest numpy
    pytest {os.path.basename(temp_filename)} 
    """

    # Create and run the container, capturing the output
    container = client.containers.create(
        image=docker_image,
        command='/bin/bash -c "{}"'.format(commands),
        tty=True,
        volumes={test_dir: {"bind": f"/tests", "mode": "rw"}},
        working_dir="/tests",
    )
    print(f"Running tests in Docker container {container.id}...")
    container.start()

    # Wait for the container to finish and capture the output
    result = container.wait()
    output = container.logs()

    # Clean up
    container.remove()
    os.remove(temp_filename)

    return output.decode("utf-8")


def run_tests(source_code, docker_image):
    output = _run_tests_in_docker(source_code, docker_image=docker_image)

    result = _extract_pytest_output(output)

    return result


if __name__ == "__main__":
    source_code = """
import numpy as np
import pytest

def test_add():
    assert 1 + 1 == 2
    """
    results = run_tests(source_code, docker_image="python:3.8")
    print(results)
