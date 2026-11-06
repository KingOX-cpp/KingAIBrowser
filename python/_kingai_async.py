"""Async facade over the same synchronous SDK, with cancellation-safe ownership."""
import asyncio


class AsyncKingAI:
    def __init__(self, *args, **options):
        from kingai_browser import KingAI
        self._sync = KingAI(*args, **options)
        self._lock = asyncio.Lock()

    async def _run(self, function, *args, **options):
        async with self._lock:
            task = asyncio.create_task(asyncio.to_thread(function, *args, **options))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                # A cancelled Python await does not undo an input already sent.
                # Retain the lock until the worker finishes; never auto-replay.
                while not task.done():
                    try:
                        await asyncio.shield(task)
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        break
                if task.done() and not task.cancelled():
                    task.exception()  # retrieve a failure without hiding cancellation
                raise

    async def connect(self):
        await self._run(self._sync.connect)
        return self

    async def close(self):
        await self._run(self._sync.close)

    async def __aenter__(self):
        return await self.connect()

    async def __aexit__(self, *exc):
        await self.close()

    async def call(self, name, arguments=None):
        return await self._run(self._sync.call, name, arguments)

    async def tools(self):
        return await self._run(self._sync.tools)

    async def profiles(self):
        return await self._run(self._sync.profiles)

    async def info(self):
        return await self._run(self._sync.info)

    async def profile(self, profile_id):
        return await self._run(self._sync.profile, profile_id)

    async def create_profile(self, name, **options):
        return await self._run(self._sync.create_profile, name, **options)

    async def update_profile(self, profile_id, **options):
        return await self._run(self._sync.update_profile, profile_id, **options)

    async def delete_profile(self, profile_id, **options):
        return await self._run(self._sync.delete_profile, profile_id, **options)

    async def sessions(self):
        return await self._run(self._sync.sessions)

    async def start(self, *args, **options):
        return AsyncBrowserSession(self, await self._run(self._sync.start, *args, **options))

    async def attach(self, session_id):
        return AsyncBrowserSession(self, await self._run(self._sync.attach, session_id))

    async def request_status(self, request_id):
        return await self._run(self._sync.request_status, request_id)

    async def skills(self):
        return await self._run(self._sync.skills)

    async def describe_skill(self, skill_id):
        return await self._run(self._sync.describe_skill, skill_id)

    async def run_skill(self, profile_id, skill_id, **options):
        return await self._run(self._sync.run_skill, profile_id, skill_id, **options)

    async def skill_status(self, run_id):
        return await self._run(self._sync.skill_status, run_id)

    async def cancel_skill(self, run_id):
        return await self._run(self._sync.cancel_skill, run_id)

    async def skill_runs(self):
        return await self._run(self._sync.skill_runs)


class AsyncBrowserSession:
    def __init__(self, client, session):
        self.client, self._sync = client, session
        self.session_id, self.info = session.session_id, session.info

    async def call(self, name, **arguments):
        return await self.client._run(self._sync.call, name, **arguments)

    def __getattr__(self, name):
        # Forward only the public session convenience API, never private state.
        allowed = {"tabs", "new_tab", "activate_tab", "close_tab", "goto", "read", "snapshot", "query",
                   "click", "fill", "type", "evaluate", "evaluate_preview", "wait", "screenshot", "scroll",
                   "key", "hover", "pdf", "cookies", "storage", "upload", "download", "detach", "close"}
        if name not in allowed:
            raise AttributeError(name)
        async def invoke(*args, **options):
            return await self.client._run(getattr(self._sync, name), *args, **options)
        return invoke
