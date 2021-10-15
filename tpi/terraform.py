import asyncio
import os
import sys
from itertools import repeat
from typing import TYPE_CHECKING, Iterator, Optional, Union

from funcy import cat, first

if TYPE_CHECKING:
    from os import PathLike

StrPath = Union[str, "PathLike[str]"]


class TPIException(Exception):
    pass


class TerraformBackend:
    """Class for managing a named TPI iterative-machine resource."""

    def __init__(self, working_dir: StrPath, **kwargs):
        from tpi import TerraformProviderIterative

        self.working_dir = working_dir
        os.makedirs(self.working_dir, exist_ok=True)
        self.tf = TerraformProviderIterative(working_dir=self.working_dir)

    def create(self, name: Optional[str] = None, **config):
        """Create and start an instance of the specified machine."""
        from python_terraform import IsFlagged

        from tpi import render_json

        assert name and "cloud" in config
        tf_file = os.path.join(self.working_dir, "main.tf.json")
        with open(tf_file, "w", encoding="utf-8") as fobj:
            fobj.write(render_json(name=name, **config, indent=2))
        self.tf.cmd("init")
        self.tf.cmd("apply", auto_approve=IsFlagged)

    def destroy(self, name: Optional[str] = None, **config):
        """Stop and destroy all instances of the specified machine."""
        from python_terraform import IsFlagged

        assert name

        if first(self.tf.iter_instances(name)):
            self.tf.cmd("destroy", auto_approve=IsFlagged)

    def instances(self, name: Optional[str] = None, **config) -> Iterator[dict]:
        """Iterate over status of all instances of the specified machine."""
        assert name

        yield from self.tf.iter_instances(name)

    def close(self):
        pass

    def run_shell(self, name: Optional[str] = None, **config):
        """Spawn an interactive SSH shell for the specified machine."""
        from tpi import TerraformProviderIterative

        resource = self.default_resource(name)
        with TerraformProviderIterative.pemfile(resource) as pem:
            self._shell(
                host=resource["instance_ip"],
                username="ubuntu",
                client_keys=pem,
                known_hosts=None,
            )

    def default_resource(self, name):
        from tpi import TPIError

        resource = first(self.instances(name))
        if not resource:
            raise TPIError(f"No active '{name}' instances")
        return resource

    def _shell(self, *args, **kwargs):
        """Sync wrapper for an SSH shell session.

        The default 'ssh' client will be used when available in PATH,
        otherwise a basic shell session will be run via asyncssh.

        Args will be passed into asyncssh.connect() or converted into the
        equivalent OpenSSH CLI flags.
        """
        from shutil import which

        if which("ssh"):
            return self._shell_default(*args, **kwargs)

        from asyncssh import Error as AsyncSshError

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._shell_async(*args, **kwargs))
        except (OSError, AsyncSshError) as exc:
            raise TPIException("SSH connection failed") from exc
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    async def _shell_async(self, *args, **kwargs):
        from asyncssh import connect

        async with connect(*args, **kwargs) as conn:
            await conn.run(
                term_type=os.environ.get("TERM", "xterm"),
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

    def _shell_default(
        *args, host=None, username=None, port=None, client_keys=None, **kwargs
    ):
        from subprocess import run

        assert host

        cmd = ["ssh"]
        if client_keys:
            if isinstance(client_keys, str):
                client_keys = [client_keys]
            cmd.extend(cat(zip(repeat("-i"), client_keys)))
        user = f"{username}@" if username else ""
        port = f":{port}" if port is not None else ""
        cmd.append(f"{user}{host}{port}")
        run(cmd)

    def state_mv(self, source, destination, **kwargs):
        """Retain an existing remote object but track it as a
        different resource instance address.
        """
        assert source and destination
        self.tf.cmd("state mv", source, destination)
