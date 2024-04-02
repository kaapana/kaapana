import json
import asyncio
from asyncio import Lock
from typing import List


class MappingsManager:
    def __init__(self, file_path, save_interval=300):
        self.file_path = file_path
        self.mappings = {}  # From "seriesInstanceUID|sopInstanceUID" to numeric ID
        self.reverse_mappings = (
            {}
        )  # From numeric ID back to "seriesInstanceUID|sopInstanceUID"
        self.lock = Lock()
        self._load_mappings()
        self.save_interval = save_interval  # Save interval in seconds
        self._start_periodic_save()

    def _load_mappings(self):
        try:
            with open(self.file_path, "r") as file:
                self.mappings = json.load(file)
            # Populate reverse mappings
            self.reverse_mappings = {v: k for k, v in self.mappings.items()}
        except FileNotFoundError:
            self.mappings = {}
            self.reverse_mappings = {}

    def _start_periodic_save(self):
        asyncio.create_task(self._periodic_save())

    async def _periodic_save(self):
        while True:
            await asyncio.sleep(self.save_interval)
            await self._save_mappings()

    async def shutdown(self):
        await self._save_mappings()

    async def get_numeric_id(self, seriesInstanceUID, sopInstanceUID):
        key = f"{seriesInstanceUID}|{sopInstanceUID}"
        async with self.lock:
            if key in self.mappings:
                return self.mappings[key]
            else:
                numeric_id = len(self.mappings) + 1
                self.mappings[key] = numeric_id
                self.reverse_mappings[numeric_id] = key
                # Removed immediate saving to defer to periodic save
                return numeric_id

    async def _save_mappings(self):
        async with self.lock:
            with open(self.file_path, "w") as file:
                json.dump(self.mappings, file)
                print(f"Mappings saved to {self.file_path}")

    async def search(self, numeric_ids: List[int]):
        # Retrieve (seriesInstanceUID, sopInstanceUID) pairs based on numeric IDs
        async with self.lock:
            return [
                self.reverse_mappings.get(numeric_id)
                for numeric_id in numeric_ids
                if numeric_id in self.reverse_mappings
            ]
