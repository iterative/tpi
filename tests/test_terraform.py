import json
import os

import pytest
from mock import ANY, MagicMock
from python_terraform import IsFlagged

from tpi import TerraformProviderIterative, TPIError

TEST_RESOURCE_STATE = """{
  "version": 4,
  "terraform_version": "1.0.4",
  "serial": 12,
  "lineage": "7f93cd8b-3abf-b4a4-d939-60b55699c3ed",
  "outputs": {},
  "resources": [
    {
      "mode": "managed",
      "type": "iterative_machine",
      "name": "test-resource",
      "provider": "provider[\\"registry.terraform.io/iterative/iterative\\"]",
      "instances": [
        {
          "schema_version": 0,
          "attributes": {
            "aws_security_group": null,
            "cloud": "aws",
            "id": "iterative-2jyhw8j9ieov6",
            "image": "ubuntu-bionic-18.04-amd64-server-20210818",
            "instance_gpu": null,
            "instance_hdd_size": 35,
            "instance_ip": "123.123.123.123",
            "instance_launch_time": "2021-08-25T07:13:03Z",
            "instance_type": "m",
            "name": "test-resource",
            "region": "us-west",
            "spot": false,
            "spot_price": -1,
            "ssh_name": null,
            "ssh_private": "-----BEGIN RSA PRIVATE KEY-----\\n",
            "startup_script": "IyEvYmluL2Jhc2g=",
            "timeouts": null
          },
          "sensitive_attributes": [],
          "private": ""
        }
      ]
    }
  ]
}
"""


@pytest.fixture
def terraform(tmp_path, mocker):
    from python_terraform import Terraform

    from tpi.terraform import TerraformBackend

    cmd_mock = mocker.patch.object(Terraform, "cmd", return_value=(0, None, None))
    tf = TerraformBackend(tmp_path)
    tf.cmd_mock = cmd_mock
    yield tf


@pytest.fixture
def resource(tmp_path):
    name = "test-resource"
    path = tmp_path / name / "terraform.tfstate"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEST_RESOURCE_STATE, encoding="utf-8")
    yield name


def test_run_cmd(mocker):
    from python_terraform import Terraform

    tf = TerraformProviderIterative()
    cmd_mock = mocker.patch.object(Terraform, "cmd", return_value=(0, None, None))
    tf.cmd("init")
    cmd_mock.assert_called_once_with("init", capture_output=False)

    cmd_mock = mocker.patch.object(Terraform, "cmd", return_value=(-1, None, None))
    with pytest.raises(TPIError):
        tf.cmd("init")


def test_make_pemfile():
    content = "foo\nbar\n"
    with TerraformProviderIterative.pemfile({"ssh_private": content}) as path:
        with open(path, "r") as fobj:
            assert fobj.read() == content


def test_make_tf(terraform):
    name = "foo"
    with terraform.make_tf(name) as tf:
        assert tf.working_dir == os.path.join(terraform.tmp_dir, name)


def test_create(tmp_path, terraform):
    name = "foo"
    terraform.create(name=name, cloud="aws")
    terraform.cmd_mock.assert_any_call("init", capture_output=False)
    terraform.cmd_mock.assert_any_call(
        "apply", capture_output=False, auto_approve=IsFlagged
    )
    assert (tmp_path / name / "main.tf.json").exists()
    with open(tmp_path / name / "main.tf.json") as fobj:
        data = json.load(fobj)
    assert data["resource"]["iterative_machine"] == {
        name: {"name": name, "cloud": "aws"},
    }


def test_destroy(terraform, resource):
    terraform.destroy(name=resource, cloud="aws")
    terraform.cmd_mock.assert_called_with(
        "destroy", capture_output=False, auto_approve=IsFlagged
    )


def test_instances(terraform, resource):
    data = json.loads(TEST_RESOURCE_STATE)
    expected = data["resources"][0]["instances"][0]["attributes"]
    assert list(terraform.instances(resource)) == [expected]


def test_shell_async(terraform, resource, mocker):
    data = json.loads(TEST_RESOURCE_STATE)
    expected = data["resources"][0]["instances"][0]["attributes"]
    mock_connect = mocker.patch("asyncssh.connect", return_value=MagicMock())
    mocker.patch("shutil.which", return_value=None)
    terraform.run_shell(name=resource)
    mock_connect.assert_called_once_with(
        host=expected["instance_ip"],
        username="ubuntu",
        client_keys=ANY,
        known_hosts=None,
    )


def test_shell_default(terraform, resource, mocker):
    data = json.loads(TEST_RESOURCE_STATE)
    expected = data["resources"][0]["instances"][0]["attributes"]
    mock_run = mocker.patch("subprocess.run")
    mocker.patch("shutil.which", return_value="/usr/bin/ssh")
    terraform.run_shell(name=resource)
    mock_run.assert_called_once_with(
        [
            "ssh",
            "-i",
            ANY,
            f"ubuntu@{expected['instance_ip']}",
        ]
    )
