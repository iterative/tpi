import asyncio
import os
import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterator, Optional, Union

if TYPE_CHECKING:
    from os import PathLike

StrPath = Union[str, "PathLike[str]"]


class TPIException(Exception):
    pass


class BaseMachineBackend(ABC):
    def __init__(self, tmp_dir: StrPath, **kwargs):
        self.tmp_dir = tmp_dir
        os.makedirs(self.tmp_dir, exist_ok=True)

    @abstractmethod
    def create(self, name: Optional[str] = None, **config):
        """Create and start an instance of the specified machine."""

    @abstractmethod
    def destroy(self, name: Optional[str] = None, **config):
        """Stop and destroy all instances of the specified machine."""

    @abstractmethod
    def instances(self, name: Optional[str] = None, **config) -> Iterator[dict]:
        """Iterate over status of all instances of the specified machine."""

    def close(self):
        pass

    @abstractmethod
    def run_shell(self, name: Optional[str] = None, **config):
        """Spawn an interactive SSH shell for the specified machine."""

    def _shell(self, *args, **kwargs):
        """Sync wrapper for an asyncssh shell session.

        Args will be passed into asyncssh.connect().
        """
        import asyncssh

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._shell_async(*args, **kwargs))
        except (OSError, asyncssh.Error) as exc:
            raise TPIException("SSH connection failed") from exc
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    async def _shell_async(self, *args, **kwargs):
        import asyncssh

        async with asyncssh.connect(*args, **kwargs) as conn:
            await conn.run(
                term_type=os.environ.get("TERM", "xterm"),
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
